"""
Verifica i dati fiscali dei fornitori leggendo le fatture PDF dalle caselle Gmail.

Per ogni fornitore nella lista hard-coded (o passato via --supplier):
1. Cerca in Gmail (personal + business) le email con PDF allegato dal dominio del fornitore
2. Scarica i PDF più recenti in .tmp/invoices/<supplier>/
3. Passa ogni PDF a Claude Opus 4.6 (document block) chiedendo in tool-use strutturato:
   legal_name, country_iso, vat_number, iva_applied, iva_amount, reverse_charge_note,
   invoice_number, invoice_date, total_gross, notes
4. Scrive il report in .tmp/supplier_verification.json e stampa una tabella.

Usage:
    python tools/verify_suppliers_from_email.py                 # batch su tutta la lista
    python tools/verify_suppliers_from_email.py --supplier openai
    python tools/verify_suppliers_from_email.py --supplier openai --max-per-supplier 1

Richiede:
    - Token Gmail personal + business (python tools/gmail_oauth_setup.py --account ...)
    - ANTHROPIC_API_KEY in .env
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "tools"))

from gmail_client import load_service, search_messages, download_attachments, get_message  # noqa: E402

# ---------------------------------------------------------------------------
# Mailift identity — usato per filtrare i PDF non intestati a noi
# ---------------------------------------------------------------------------
MAILIFT_VAT = "18160081008"
MAILIFT_NAME_TOKENS = ["mailift"]  # case insensitive


# ---------------------------------------------------------------------------
# Supplier catalog — lista canonica da verificare
# ---------------------------------------------------------------------------
@dataclass
class SupplierQuery:
    key: str                     # slug interno
    display_name: str            # nome "umano"
    domains: list[str]           # domini da cui può arrivare la fattura (match from:)
    extra_keywords: list[str] = field(default_factory=list)  # se i domini non bastano


SUPPLIERS: list[SupplierQuery] = [
    # Extra-UE sospetti (priorità massima — la correzione parte da qui)
    SupplierQuery("elevenlabs",  "ElevenLabs",           ["elevenlabs.io"], ["ElevenLabs", "eleven labs"]),
    SupplierQuery("gamma",       "Gamma Tech",           ["gamma.app"], ["Gamma"]),
    SupplierQuery("openai",      "OpenAI",               ["openai.com"], ["OpenAI", "ChatGPT"]),
    SupplierQuery("mailsupply",  "Sp Josh Von Mailsupply",["mailsupply.co"], ["Josh Von", "Mailsupply"]),
    SupplierQuery("lovable",     "Lovable Labs",         ["lovable.dev", "lovable.so"], ["Lovable"]),
    SupplierQuery("higgsfield",  "Higgsfield",           ["higgsfield.ai"], ["Higgsfield"]),
    SupplierQuery("hostinger",   "Hostinger",            ["hostinger.com"], ["Hostinger"]),
    SupplierQuery("myleadfox",   "Myleadfox",            ["myleadfox.com", "myleadfox.io"], ["Myleadfox", "Lead Fox"]),
    # UE — controllo incrociato del pattern
    SupplierQuery("meta",        "Meta Platforms Ireland",["facebookmail.com", "facebook.com", "meta.com"], ["Meta"]),
    SupplierQuery("google",      "Google Ireland",       ["google.com"], ["Google Ads", "Google Ireland"]),
    SupplierQuery("apify",       "Apify Technologies",   ["apify.com"]),
    SupplierQuery("dkv",         "DKV Euro Service",     ["dkv-mobility.com", "dkv-euroservice.com", "dkv.com"]),
    SupplierQuery("revolut",     "Revolut Payments",     ["revolut.com"]),
    SupplierQuery("make",        "Make.com (Celonis)",   ["make.com", "integromat.com"]),
    SupplierQuery("waalaxy",     "Waalaxy",              ["waalaxy.com"]),
    SupplierQuery("dropbox",     "Dropbox",              ["dropboxsign.com", "hellosign.com", "dropbox.com"]),
]


def build_queries(s: SupplierQuery) -> list[str]:
    """Genera query Gmail in ordine di precisione decrescente."""
    from_clause = " OR ".join(f"from:{d}" for d in s.domains)
    queries: list[str] = [
        f"({from_clause}) has:attachment filename:pdf newer_than:2y",
        f"({from_clause}) has:attachment newer_than:2y",
        # Subject-based sul dominio (alcune ricevute hanno da noreply@ con subject del fornitore)
        f"({from_clause}) (invoice OR receipt OR fattura OR ricevuta) newer_than:2y",
    ]
    if s.extra_keywords:
        kw_clause = " OR ".join(f'"{k}"' for k in s.extra_keywords)
        queries.append(
            f"(subject:(invoice OR receipt OR fattura OR ricevuta) {kw_clause}) "
            f"has:attachment filename:pdf newer_than:2y"
        )
        queries.append(
            f"({kw_clause}) has:attachment filename:pdf newer_than:2y"
        )
        # Ricerca full-text senza attachment per vedere almeno se il fornitore esiste in mailbox
        queries.append(
            f"({kw_clause}) (invoice OR receipt OR fattura OR ricevuta) newer_than:2y"
        )
    return queries


# ---------------------------------------------------------------------------
# Local PDF pre-filter (evita di bruciare credit Claude su PDF non rilevanti)
# ---------------------------------------------------------------------------
def pdf_is_for_mailift(pdf_path: Path) -> tuple[bool, str]:
    """Estrae il testo del PDF con pdfplumber e controlla se contiene la P.IVA o il nome Mailift.
    Ritorna (match, reason). Usa pdfplumber che è già in requirements."""
    try:
        import pdfplumber
    except ImportError:
        # Se non c'è pdfplumber lasciamo passare tutto
        return True, "pdfplumber not available, skipping filter"
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages[:3])
    except Exception as e:
        return True, f"pdf parse error ({e}), keeping to be safe"
    text_lower = text.lower()
    if MAILIFT_VAT in text.replace(" ", "") or MAILIFT_VAT in text:
        return True, f"match VAT {MAILIFT_VAT}"
    for token in MAILIFT_NAME_TOKENS:
        if token in text_lower:
            return True, f"match name '{token}'"
    # Se non troviamo né Mailift né la P.IVA, scarta
    return False, "no Mailift identifier in Bill to"


# ---------------------------------------------------------------------------
# Claude analysis
# ---------------------------------------------------------------------------
EXTRACT_TOOL = {
    "name": "report_invoice_fiscal_data",
    "description": "Report all fiscal/legal details extracted from the invoice PDF.",
    "input_schema": {
        "type": "object",
        "properties": {
            "supplier_legal_name": {"type": "string", "description": "Ragione sociale esatta come scritta sulla fattura"},
            "supplier_country_iso": {"type": "string", "description": "Codice paese ISO-2 del cedente (es. US, IE, DE, CZ)"},
            "supplier_country_name": {"type": "string"},
            "supplier_vat_number": {"type": "string", "description": "P.IVA/VAT/EIN del fornitore — stringa vuota se assente"},
            "supplier_address_street": {"type": "string"},
            "supplier_address_city": {"type": "string"},
            "supplier_address_postal_code": {"type": "string"},
            "iva_applied": {"type": "boolean", "description": "True se sulla fattura c'è una riga IVA/VAT > 0 nel totale"},
            "iva_rate_percent": {"type": "number", "description": "Aliquota IVA applicata in %, 0 se non applicata"},
            "iva_amount": {"type": "number", "description": "Importo IVA in valuta fattura"},
            "reverse_charge_note": {"type": "boolean", "description": "True se la fattura menziona reverse charge / VAT to be paid by recipient / art.7-ter / art.44"},
            "reverse_charge_text": {"type": "string", "description": "Testo letterale che menziona il reverse charge, se presente"},
            "invoice_number": {"type": "string"},
            "invoice_date": {"type": "string", "description": "Formato YYYY-MM-DD se possibile"},
            "currency": {"type": "string"},
            "total_net": {"type": "number"},
            "total_gross": {"type": "number"},
            "notes": {"type": "string", "description": "Note libere: qualunque cosa insolita o ambigua"},
        },
        "required": [
            "supplier_legal_name", "supplier_country_iso", "supplier_vat_number",
            "iva_applied", "iva_rate_percent", "reverse_charge_note",
            "invoice_number", "invoice_date", "total_gross",
        ],
    },
}


def analyze_pdf(pdf_path: Path) -> dict[str, Any]:
    """Invia il PDF a Claude con document block + tool use, ritorna il dict strutturato."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")

    pdf_b64 = base64.standard_b64encode(pdf_path.read_bytes()).decode("ascii")

    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "report_invoice_fiscal_data"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                },
                {
                    "type": "text",
                    "text": (
                        "Analizza questa fattura e riporta i dati fiscali tramite il tool "
                        "report_invoice_fiscal_data. È critico identificare correttamente il paese "
                        "del cedente (ISO-2) e se sulla fattura è applicata l'IVA o se invece c'è "
                        "una dicitura di reverse charge (IVA a carico del cessionario)."
                    ),
                },
            ],
        }],
    )

    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise RuntimeError(f"Claude non ha usato il tool per {pdf_path.name}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def find_invoices_for_supplier(services: dict[str, Any], s: SupplierQuery, max_msgs: int = 3) -> list[tuple[str, str, Path]]:
    """Cerca in entrambi gli account, scarica fino a max_msgs PDF. Ritorna [(account, msg_id, pdf_path)]."""
    out_dir = ROOT / ".tmp" / "invoices" / s.key
    out_dir.mkdir(parents=True, exist_ok=True)
    found: list[tuple[str, str, Path]] = []
    seen_msg_ids: set[str] = set()
    discarded: list[tuple[str, str]] = []

    # Ordine: business prima, personal come fallback
    ordered_accounts = sorted(services.keys(), key=lambda a: 0 if a == "business" else 1)

    for account in ordered_accounts:
        svc = services[account]
        if len(found) >= max_msgs:
            break
        for query in build_queries(s):
            if len(found) >= max_msgs:
                break
            try:
                msgs = search_messages(svc, query, max_results=15)
            except Exception as e:
                print(f"  [{account}] query error: {e}")
                continue
            if not msgs:
                continue
            print(f"  [{account}] query '{query[:70]}...' → {len(msgs)} msg")
            for m in msgs:
                if len(found) >= max_msgs:
                    break
                if m["id"] in seen_msg_ids:
                    continue
                seen_msg_ids.add(m["id"])
                try:
                    pdfs = download_attachments(svc, m["id"], out_dir, only_pdf=True)
                except Exception as e:
                    print(f"    download error msg {m['id']}: {e}")
                    continue
                for p in pdfs:
                    ok, reason = pdf_is_for_mailift(p)
                    if not ok:
                        discarded.append((p.name, reason))
                        # Sposta in quarantena invece di cancellare
                        rej_dir = ROOT / ".tmp" / "invoices_rejected" / s.key
                        rej_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            p.rename(rej_dir / p.name)
                        except Exception:
                            pass
                        continue
                    print(f"    ✓ {p.name} ({reason})")
                    found.append((account, m["id"], p))
                    if len(found) >= max_msgs:
                        break
            if found:
                break  # prima query che matcha per quell'account, non proviamo le fallback
    if discarded:
        print(f"  Scartati (no Mailift bill to): {len(discarded)}")
        for name, reason in discarded[:3]:
            print(f"    - {name}: {reason}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplier", help="Processa solo il fornitore con questo key (es. openai)")
    ap.add_argument("--max-per-supplier", type=int, default=2, help="Max PDF da analizzare per fornitore (default 2)")
    ap.add_argument("--skip-analysis", action="store_true", help="Solo download, niente Claude")
    args = ap.parse_args()

    if args.supplier:
        lst = [s for s in SUPPLIERS if s.key == args.supplier]
        if not lst:
            print(f"Fornitore '{args.supplier}' non trovato. Keys: {[s.key for s in SUPPLIERS]}")
            return 1
    else:
        lst = SUPPLIERS

    print("Carico Gmail services...")
    services: dict[str, Any] = {}
    for account in ("personal", "business"):
        try:
            services[account] = load_service(account)
            print(f"  {account}: OK")
        except Exception as e:
            print(f"  {account}: ERRORE {e}")

    if not services:
        print("Nessun account Gmail disponibile. Aborting.")
        return 1

    report: dict[str, Any] = {}
    for s in lst:
        print(f"\n=== {s.display_name} ({s.key}) ===")
        invoices = find_invoices_for_supplier(services, s, max_msgs=args.max_per_supplier)
        if not invoices:
            print("  Nessuna fattura trovata.")
            report[s.key] = {"display_name": s.display_name, "invoices": [], "error": "no_invoices"}
            continue
        print(f"  {len(invoices)} PDF scaricati.")
        analyzed: list[dict[str, Any]] = []
        if args.skip_analysis:
            for acc, mid, p in invoices:
                analyzed.append({"account": acc, "msg_id": mid, "pdf": str(p.relative_to(ROOT))})
        else:
            for acc, mid, p in invoices:
                print(f"  Analizzo {p.name} ({acc})...")
                try:
                    data = analyze_pdf(p)
                    data["_account"] = acc
                    data["_msg_id"] = mid
                    data["_pdf"] = str(p.relative_to(ROOT))
                    analyzed.append(data)
                    iva = "CON IVA" if data.get("iva_applied") else "NO IVA"
                    rc = "RC" if data.get("reverse_charge_note") else ""
                    print(f"    → {data.get('supplier_country_iso')} | {iva} {rc} | {data.get('supplier_legal_name')}")
                except Exception as e:
                    print(f"    ERRORE analisi: {e}")
                    analyzed.append({"_account": acc, "_msg_id": mid, "_pdf": str(p.relative_to(ROOT)), "error": str(e)})
        report[s.key] = {"display_name": s.display_name, "invoices": analyzed}

    out_path = ROOT / ".tmp" / "supplier_verification.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport salvato in {out_path.relative_to(ROOT)}")

    # Tabella riepilogo
    print("\n" + "=" * 100)
    print(f"{'KEY':15} {'LEGAL NAME':40} {'ISO':5} {'IVA%':6} {'RC':4} {'VAT_NUMBER':20}")
    print("=" * 100)
    for key, r in report.items():
        invs = [i for i in r.get("invoices", []) if "supplier_country_iso" in i]
        if not invs:
            print(f"{key:15} {'(nessuna fattura)':40}")
            continue
        for inv in invs[:1]:  # prima valida
            print(
                f"{key:15} "
                f"{(inv.get('supplier_legal_name') or '')[:40]:40} "
                f"{(inv.get('supplier_country_iso') or '-'):5} "
                f"{str(inv.get('iva_rate_percent') or 0):6} "
                f"{'YES' if inv.get('reverse_charge_note') else '-':4} "
                f"{(inv.get('supplier_vat_number') or '-'):20}"
            )
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
