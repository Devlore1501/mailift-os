"""
Classifica le transazioni di un estratto conto e identifica quelle che
richiedono l'emissione di un'autofattura (TD17 / TD18 / TD19).

Usa Claude per analizzare descrizione + importo e produrre dati strutturati.

Output: per ogni transazione candidata
    {
        "needs_autofattura": true,
        "type_doc": "TD17"|"TD18"|"TD19",
        "supplier_name": "Google Ireland Ltd",
        "supplier_country": "IE",
        "supplier_vat_number": "IE6388047V",
        "description": "Google Ads - addebito mensile",
        "vat_rate": 22,
        "confidence": "high"|"medium"|"low",
        "reason": "spiegazione breve",
        "source_transaction": {...}
    }

Regole base usate dal prompt:
    - TD17 = servizi/beni intangibili da fornitore UE o extra-UE
    - TD18 = acquisto beni intra-UE
    - TD19 = acquisto beni da fornitore extra-UE con beni gi\u00e0 in Italia / art.17 c.2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else ROOT / ".env")

# Fornitori italiani con IVA 22% diretta che NON devono mai finire in autofattura.
# Ogni entry ha: pattern regex (case-insensitive, matchato sulla descrizione della transazione
# o sul supplier_name che Claude proporrebbe) e reason human-readable mostrata in UI.
AUTOFATTURA_BLACKLIST: list[dict] = [
    {"pattern": r"google\s+cloud\s+italy", "reason": "Google Cloud Italy Srl - IT, IVA 22% diretta"},
    {"pattern": r"google\s+workspace.*\bitaly\b", "reason": "Google Workspace IT - IVA 22% diretta"},
    {"pattern": r"google\s+workspace.*\bIT\b", "reason": "Google Workspace IT - IVA 22% diretta"},
]

SYSTEM_PROMPT = """Sei un assistente fiscale italiano specializzato in IVA e reverse charge.
Analizzi righe di estratto conto bancario e identifichi gli acquisti che obbligano
il committente italiano a emettere un'autofattura ai sensi della normativa IVA.

REGOLE:
- TD17 = acquisti di servizi (e beni intangibili) da fornitore UE o EXTRA-UE soggetti a reverse charge ex art. 17 c.2 DPR 633/72.
- TD18 = acquisti intra-UE di BENI (merci fisiche) da fornitore UE.
- TD19 = acquisti da fornitore extra-UE/UE di beni gia' presenti in Italia (art. 17 c.2 - integrazione).
- Aliquota IVA in autofattura: di norma 22%.
- NON richiedono autofattura: bonifici verso fornitori italiani, stipendi, F24, commissioni bancarie ITALIANE, giroconti, rimborsi, accrediti, pagamenti rate finanziamenti italiani, ricariche conto.
- Esempi tipici SI: Google Ireland (Ads/Workspace), Meta Platforms Ireland (Facebook Ads), Microsoft Ireland, Amazon Web Services EMEA SARL, LinkedIn Ireland, Apple Distribution International, Stripe Payments Europe, OpenAI L.L.C., Anthropic PBC, Cloudflare, GitHub, Figma, Notion Labs, Adobe Ireland, Dropbox Ireland, Hostinger International, Make.com (Celonis s.r.o.), Lovable AB, Apify Technologies, ElevenLabs Inc, Higgsfield, Revolut Bank UAB / Revolut Payments UAB.
- DKV Euro Service e' un fornitore tedesco di servizi flotta -> TD17.
- "Commissione Revolut Business" -> Revolut e' lituano/UE -> TD17.

FORNITORI DA ESCLUDERE (skipped_italian=true, NON vanno in autofattura):
- Google Cloud Italy Srl (IT, IVA 22% diretta)
- Google Workspace IT / Google Workspace Italy (IT, IVA 22% diretta)
- Qualsiasi fornitore italiano che emetta fattura con IVA 22% diretta al committente IT Mailift (quindi con P.IVA IT e dicitura italiana nella descrizione): flagga con skipped_italian=true e skip_reason chiaro.

Per ciascun fornitore conosciuto, fornisci P.IVA UE e codice paese ISO se la conosci con certezza.
Se non sei sicuro su P.IVA, lascia stringa vuota.
La confidence deve essere "high" (fornitore noto e chiaro), "medium" (probabile ma non certissimo) o "low" (ipotesi).
INCLUDI nella risposta anche le righe skipped_italian=true con il motivo (serve per trasparenza UI), ma NON quelle che proprio non richiedono autofattura (bonifici IT, F24, ecc.)."""


def _build_tool_schema() -> dict:
    return {
        "name": "report_autofatture",
        "description": "Restituisce l'elenco delle transazioni che richiedono emissione di autofattura passiva (TD17/TD18/TD19).",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "description": "Una entry per ciascuna transazione che richiede autofattura. Escludi tutte le altre.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_index": {"type": "integer", "description": "Indice della transazione nella lista di input"},
                            "type_doc": {"type": "string", "enum": ["TD17", "TD18", "TD19"]},
                            "supplier_name": {"type": "string", "description": "Ragione sociale completa del fornitore reale (es. 'Meta Platforms Ireland Limited')"},
                            "supplier_country": {"type": "string", "description": "Codice paese ISO 3166-1 alpha-2 (es. IE, US, DE)"},
                            "supplier_vat_number": {"type": "string", "description": "P.IVA con prefisso paese (es. IE9692928F). Stringa vuota se non sicuro."},
                            "description": {"type": "string", "description": "Descrizione sintetica del servizio (es. 'Pubblicità Facebook Ads')"},
                            "vat_rate": {"type": "number", "description": "Aliquota IVA da applicare in autofattura, di norma 22"},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                            "reason": {"type": "string", "description": "Motivo breve della classificazione"},
                            "skipped_italian": {"type": "boolean", "description": "True se il fornitore e' italiano con IVA 22% diretta e NON va in autofattura (verra' mostrato in UI nel box trasparenza, non nel preview)."},
                            "skip_reason": {"type": "string", "description": "Se skipped_italian=true, motivo dell'esclusione."},
                        },
                        "required": ["source_index", "type_doc", "supplier_name", "supplier_country", "description", "vat_rate", "confidence"],
                    },
                }
            },
            "required": ["candidates"],
        },
    }


def _matches_blacklist(text: str) -> dict | None:
    import re
    if not text:
        return None
    for entry in AUTOFATTURA_BLACKLIST:
        if re.search(entry["pattern"], text, flags=re.IGNORECASE):
            return entry
    return None


def classify_split(transactions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Come classify() ma ritorna (candidates, skipped_italian).

    - candidates: righe che vanno davvero in autofattura (skipped_italian=False).
    - skipped_italian: fornitori italiani con IVA 22% diretta, esclusi ma mostrati in UI.
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")

    indexed = [{"index": i, **t} for i, t in enumerate(transactions)]
    tool = _build_tool_schema()

    msg = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": "report_autofatture"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Ecco le transazioni in uscita dell'estratto conto. Identifica SOLO quelle "
                    "che richiedono autofattura passiva e chiamale tramite il tool report_autofatture. "
                    "Per ogni candidate usa source_index = il valore di 'index' nella transazione.\n\n"
                    f"Transazioni:\n{json.dumps(indexed, ensure_ascii=False, indent=2)}"
                ),
            }
        ],
    )

    tool_input = None
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_autofatture":
            tool_input = block.input
            break
    if tool_input is None:
        raise RuntimeError(f"Il modello non ha invocato il tool. Stop reason: {msg.stop_reason}")

    if os.environ.get("CLASSIFY_DEBUG"):
        print(f"--- TOOL INPUT: {len(tool_input.get('candidates', []))} candidates ---")

    enriched_candidates: list[dict] = []
    skipped: list[dict] = []
    for item in tool_input.get("candidates", []):
        idx = item.get("source_index")
        src = transactions[idx] if idx is not None and 0 <= idx < len(transactions) else None
        item["source_transaction"] = src

        # Hard blacklist match (pattern regex) sovrascrive la decisione del modello
        haystack = " ".join([
            str(item.get("supplier_name") or ""),
            str((src or {}).get("description") or ""),
        ])
        bl = _matches_blacklist(haystack)
        if bl is not None:
            item["skipped_italian"] = True
            item["skip_reason"] = item.get("skip_reason") or bl["reason"]

        if item.get("skipped_italian"):
            skipped.append(item)
        else:
            enriched_candidates.append(item)
    return enriched_candidates, skipped


def classify(transactions: list[dict]) -> list[dict]:
    """Back-compat: ritorna solo le candidate non-skipped."""
    candidates, _ = classify_split(transactions)
    return candidates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="JSON delle transazioni (output di parse_bank_statement.py)")
    ap.add_argument("--out", type=Path, default=Path(".tmp/autofatture_candidates.json"))
    args = ap.parse_args()

    transactions = json.loads(args.input.read_text())
    # Restringi ai movimenti in uscita (gli unici che generano autofattura passiva)
    outflows = [t for t in transactions if t.get("amount", 0) < 0]
    print(f"Classifico {len(outflows)} movimenti in uscita...")
    result = classify(outflows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Trovate {len(result)} candidate autofatture -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
