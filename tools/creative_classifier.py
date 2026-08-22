#!/usr/bin/env python3
"""
Classifica i creative per angolo, awareness stage e tipo di hook.

Manda a Claude l'immagine (ridimensionata) + headline/body/CTA e ottiene una
classificazione strutturata. Senza questo passaggio il DB sa *cosa* e' stato
speso ma non *cosa e' stato detto*, e gli angoli non sono raggruppabili.

Costi: una chiamata per combinazione unica di (immagine, copy). I creative che
condividono immagine e copy identici riusano la stessa classificazione, quindi
il numero di chiamate e' minore del numero di creative.

CLI:
  python tools/creative_classifier.py classify
  python tools/creative_classifier.py classify --limit 5      # prova su pochi
  python tools/creative_classifier.py classify --force        # riclassifica tutto
  python tools/creative_classifier.py status
  python tools/creative_classifier.py angles
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from creative_db import connect, migrate
from pipeline_config import ensure, get

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

MAX_EDGE = 768          # oltre non serve: il testo di una statica resta leggibile
JPEG_QUALITY = 80

# Vocabolario controllato: angoli liberi renderebbero i gruppi inconfrontabili,
# che e' esattamente il problema che questo DB esiste per evitare.
ANGLES = {
    "secchio-bucato":       "Il traffico che paghi si perde: stai riempiendo un secchio bucato.",
    "revenue-nascosta":     "C'è fatturato già nella tua lista che non stai incassando.",
    "anti-newsletter":      "Non facciamo newsletter, costruiamo un sistema/metodo.",
    "dipendenza-ads":       "Sei dipendente dalle ads: slega il fatturato dal budget pubblicitario.",
    "klaviyo-mal-usato":    "Hai già Klaviyo ma lo stai usando male / al 10%.",
    "calcolatore-diagnosi": "Scopri/calcola quanto stai perdendo (strumento, audit, report).",
    "caso-studio-prova":    "Prova concreta: numeri, risultato di un cliente, case study.",
    "autorevolezza-founder":"Il founder parla in prima persona, autorità/esperienza.",
    "altro":                "Nessuno degli angoli sopra descrive il messaggio principale.",
}

AWARENESS = {
    "unaware":        "Non sa di avere il problema.",
    "problem-aware":  "Sente il problema ma non conosce la soluzione.",
    "solution-aware": "Sa che esiste una soluzione (email marketing) ma non il prodotto.",
    "product-aware":  "Conosce Mailift/l'offerta, va convinto.",
    "most-aware":     "Pronto ad agire, serve solo l'offerta.",
}

HOOKS = {
    "domanda":           "Apre con una domanda diretta al lettore.",
    "statistica":        "Apre con un dato o una percentuale.",
    "provocazione":      "Afferma qualcosa di controintuitivo o polemico.",
    "promessa-numerica": "Promette un risultato quantificato in un tempo definito.",
    "loss-aversion":     "Punta su cosa stai perdendo adesso.",
    "curiosita":         "Crea un gap di curiosità senza rivelare.",
    "dimostrazione":     "Mostra il meccanismo/processo (diagramma, screenshot).",
    "testimonianza":     "Voce di un cliente o risultato altrui.",
    "altro":             "Nessuno dei precedenti.",
}

TOOL = {
    "name": "classifica_creative",
    "description": "Registra la classificazione del creative pubblicitario.",
    "input_schema": {
        "type": "object",
        "properties": {
            "angle": {"type": "string", "enum": list(ANGLES),
                      "description": "L'angolo comunicativo principale."},
            "awareness_stage": {"type": "string", "enum": list(AWARENESS),
                                "description": "Stadio di consapevolezza del destinatario."},
            "hook_type": {"type": "string", "enum": list(HOOKS),
                          "description": "Come l'annuncio cattura l'attenzione."},
            "visual_note": {"type": "string",
                            "description": "Una frase su cosa mostra l'immagine (max 120 caratteri)."},
            "confidence": {"type": "number",
                           "description": "Confidenza da 0 a 1 nella classificazione."},
        },
        "required": ["angle", "awareness_stage", "hook_type", "visual_note", "confidence"],
    },
}


def _taxonomy_text() -> str:
    def block(title, d):
        return title + "\n" + "\n".join(f"  - {k}: {v}" for k, v in d.items())
    return "\n\n".join([block("ANGOLI:", ANGLES), block("AWARENESS:", AWARENESS), block("HOOK:", HOOKS)])


SYSTEM = f"""Sei un analista di creative pubblicitarie per Mailift, agenzia italiana di
email marketing per eCommerce DTC su Shopify e Klaviyo.

Classifichi ogni annuncio secondo questo vocabolario controllato. Usa SOLO questi valori.

{_taxonomy_text()}

Regole:
- L'angolo è il messaggio PRINCIPALE, non ogni tema toccato. Scegline uno solo.
- Giudica immagine e copy insieme: su una statica il testo nell'immagine conta
  quanto il copy dell'annuncio.
- Se il messaggio non rientra chiaramente in un angolo, usa "altro" con confidence bassa.
  Non forzare una categoria per compiacere: una classificazione sbagliata è peggio di "altro".
"""


def load_image_b64(path: Path) -> tuple[str, str]:
    """Ridimensiona e ricomprime: 2048px non aggiungono informazione utile qui."""
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"


def classify_one(client, model: str, asset: Path, headline: str, body: str, cta: str) -> dict:
    b64, media = load_image_b64(asset)
    msg = client.messages.create(
        model=model,
        max_tokens=600,
        system=SYSTEM,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "classifica_creative"},
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
            {"type": "text", "text":
                f"Classifica questo annuncio.\n\n"
                f"Headline: {headline or '(nessuna)'}\n"
                f"Corpo: {body or '(nessuno)'}\n"
                f"CTA: {cta or '(nessuna)'}"},
        ]}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("nessuna tool_use nella risposta")


def migrate_classifier(conn) -> None:
    ensure(conn)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(creatives)")}
    for col, typ in (("visual_note", "TEXT"), ("classify_confidence", "REAL"),
                     ("classified_at", "TEXT"), ("classify_error", "TEXT")):
        if col not in have:
            conn.execute(f"ALTER TABLE creatives ADD COLUMN {col} {typ}")
    conn.commit()


def classify(limit: int | None, force: bool, quiet: bool = False) -> tuple[int, int, int]:
    """Ritorna (classificati, riusati_da_cache, falliti)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY non trovata in .env")
    import anthropic

    conn = connect()
    migrate_classifier(conn)
    model = get("classifier_model", conn)

    where = "asset_path IS NOT NULL AND asset_path != ''"
    if not force:
        where += " AND (angle IS NULL OR angle = '')"
    q = f"""SELECT creative_id, ad_name, headline, body, cta, asset_path, asset_sha256
            FROM creatives WHERE {where} ORDER BY creative_id"""
    rows = conn.execute(q + (f" LIMIT {int(limit)}" if limit else "")).fetchall()

    if not rows:
        conn.close()
        return (0, 0, 0)

    client = anthropic.Anthropic(api_key=key)
    now = datetime.now().isoformat(timespec="seconds")
    cache: dict[tuple, dict] = {}
    done = reused = failed = 0

    for r in rows:
        asset = ROOT / r["asset_path"]
        if not asset.exists():
            conn.execute("UPDATE creatives SET classify_error=? WHERE creative_id=?",
                         ("asset mancante su disco", r["creative_id"]))
            conn.commit()
            failed += 1
            continue

        # Stessa immagine + stesso copy => stessa classificazione, niente chiamata.
        ckey = (r["asset_sha256"], r["headline"] or "", r["body"] or "", r["cta"] or "")
        cached = ckey in cache
        try:
            res = cache[ckey] if cached else classify_one(
                client, model, asset, r["headline"], r["body"], r["cta"])
        except Exception as e:
            conn.execute("UPDATE creatives SET classify_error=? WHERE creative_id=?",
                         (f"{type(e).__name__}: {e}"[:200], r["creative_id"]))
            conn.commit()
            failed += 1
            if not quiet:
                print(f"  ✗ {(r['ad_name'] or '')[:40]:<42} {type(e).__name__}")
            continue

        cache[ckey] = res
        reused += cached
        done += not cached
        conn.execute("""UPDATE creatives SET angle=?, awareness_stage=?, hook_type=?,
                        visual_note=?, classify_confidence=?, classified_at=?, classify_error=NULL
                        WHERE creative_id=?""",
                     (res["angle"], res["awareness_stage"], res["hook_type"],
                      res["visual_note"][:200], res["confidence"], now, r["creative_id"]))
        conn.commit()
        if not quiet:
            tag = "cache" if cached else f"{res['confidence']:.2f}"
            print(f"  ✓ {(r['ad_name'] or '')[:40]:<42} {res['angle']:<22} {tag}")

    conn.close()
    return (done, reused, failed)


def status() -> int:
    conn = connect()
    migrate_classifier(conn)
    tot = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    cls = conn.execute("SELECT COUNT(*) c FROM creatives WHERE angle IS NOT NULL AND angle != ''").fetchone()["c"]
    err = conn.execute("SELECT COUNT(*) c FROM creatives WHERE classify_error IS NOT NULL").fetchone()["c"]
    low = conn.execute("SELECT COUNT(*) c FROM creatives WHERE classify_confidence < 0.6").fetchone()["c"]
    print(f"Classificati: {cls}/{tot} · errori: {err} · confidenza < 0.6: {low}")
    conn.close()
    return 0


def angles() -> int:
    """Performance per angolo, dentro ogni classe di evento."""
    from creative_db import EVENT_CLASSES, _event_label, min_leads
    conn = connect()
    migrate_classifier(conn)
    T = min_leads()
    rows = conn.execute("""
        SELECT c.angle, c.awareness_stage, a.optimization_goal, a.custom_event_type,
               COUNT(DISTINCT c.creative_id) n,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        WHERE c.angle IS NOT NULL AND c.angle != ''
        GROUP BY c.angle, a.optimization_goal, a.custom_event_type
        ORDER BY spend DESC
    """).fetchall()
    conn.close()

    if not rows:
        print("Nessun creative classificato — lancia prima: classify")
        return 1

    buckets: dict[str, list] = {}
    for r in rows:
        k = EVENT_CLASSES.get(_event_label(r), "?")
        buckets.setdefault(k, []).append(r)

    for k in ("web", "leadform", "junk", "none", "?"):
        if k not in buckets:
            continue
        print(f"\n=== classe {k}")
        print(f"{'ANGOLO':<24} {'N':>3} {'SPESA':>8} {'LEAD':>5} {'CPL':>9}  VERDETTO")
        for r in sorted(buckets[k], key=lambda x: -(x["spend"] or 0)):
            leads, spend = r["leads"] or 0, r["spend"] or 0
            cpl = f"€{spend/leads:.2f}" if leads else "—"
            verdict = "confrontabile" if leads >= T else f"rumore ({leads}/{T})"
            print(f"{(r['angle'] or '—'):<24} {r['n']:>3} €{spend:>7.0f} {leads:>5} {cpl:>9}  {verdict}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Classificazione angoli dei creative")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--limit", type=int)
    c.add_argument("--force", action="store_true")
    sub.add_parser("status")
    sub.add_parser("angles")
    a = p.parse_args()

    if a.cmd == "classify":
        try:
            done, reused, failed = classify(a.limit, a.force)
        except RuntimeError as e:
            print(f"✗ {e}")
            return 1
        if done == reused == failed == 0:
            print("Niente da classificare (usa --force per rifare tutto).")
        else:
            print(f"\n{done} classificati via API · {reused} riusati da cache · {failed} falliti")
        return 1 if failed else 0
    if a.cmd == "status":
        return status()
    if a.cmd == "angles":
        return angles()
    return 0


if __name__ == "__main__":
    sys.exit(main())
