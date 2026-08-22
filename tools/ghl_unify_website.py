#!/usr/bin/env python3
"""Unifica il sito web sul campo standard `website`, svuotando il custom duplicato.

Il sito del lead vive in due posti: il campo standard GHL `website` (249 contatti)
e il custom "Il tuo sito Web?" (62). Chi legge l'uno non vede l'altro, e la
ricerca pre-call — che dal sito ricava P.IVA e dati camerali — ne vedeva solo il
29%. Unificando sullo standard si arriva al ~53%.

Regole:
- standard vuoto  → ci si scrive il valore del custom
- stessi domini   → niente da fare
- domini diversi  → NON si sovrascrive a occhi chiusi: vince il valore il cui
  dominio combacia con quello dell'email, o quello che non e' un segnaposto
  palese ('miodominio.it', 'agency.it'). Il resto va deciso a mano.

DRY-RUN PER DEFAULT.

Uso:
    python tools/ghl_unify_website.py            # dry-run
    python tools/ghl_unify_website.py --apply    # scrive (backup automatico)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl  # noqa: E402
from ghl_fields_audit import fetch_all_contacts  # noqa: E402

CUSTOM_FIELD = "gXkqSQ3G2cnXRsNjs8RC"  # "Il tuo sito Web?"
THROTTLE_S = 0.12

# Domini che qualcuno ha lasciato come esempio invece di compilare.
SEGNAPOSTO = {"miodominio.it", "agency.it", "example.com", "tuosito.it"}


def dominio(url: str | None) -> str:
    """Riduce un URL al solo dominio, per confrontare mele con mele."""
    if not url:
        return ""
    u = str(url).strip().lower().rstrip("/")
    for prefisso in ("https://", "http://", "www."):
        while u.startswith(prefisso):
            u = u[len(prefisso):]
    return u.split("/")[0]


def build_plan(contacts: list[dict]) -> dict:
    scrivi, conflitti, invariati, da_decidere = [], [], 0, []

    for c in contacts:
        custom = next(
            (x.get("value") for x in (c.get("customFields") or [])
             if x["id"] == CUSTOM_FIELD and x.get("value")),
            None,
        )
        if not custom:
            continue
        standard = c.get("website")
        email = c.get("email") or ""
        dom_email = email.split("@")[-1].lower()

        if not standard:
            scrivi.append({"id": c["id"], "email": email, "valore": custom, "motivo": "standard vuoto"})
        elif dominio(custom) == dominio(standard):
            invariati += 1
        else:
            # Chi dei due e' credibile? Il dominio dell'email e' l'indizio piu'
            # forte; un segnaposto palese perde comunque.
            custom_vince = (
                dominio(custom) == dom_email
                or dominio(standard) in SEGNAPOSTO
            )
            standard_vince = dominio(standard) == dom_email
            voce = {
                "id": c["id"], "email": email,
                "custom": custom, "standard": standard,
            }
            if custom_vince and not standard_vince:
                voce["motivo"] = (
                    "dominio custom = dominio email" if dominio(custom) == dom_email
                    else f"standard e' un segnaposto ({dominio(standard)})"
                )
                conflitti.append(voce)
            else:
                da_decidere.append(voce)

    return {
        "scrivi": scrivi,
        "conflitti": conflitti,
        "invariati": invariati,
        "da_decidere": da_decidere,
    }


def snapshot(contacts: list[dict]) -> Path:
    """Il backup dei custom field NON copre i campi standard: serve il suo."""
    out = PROJECT_ROOT / ".tmp" / f"ghl_website_backup_{date.today().isoformat()}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps(
            [{"id": c["id"], "email": c.get("email"), "website": c.get("website")}
             for c in contacts],
            indent=1, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Unifica il sito web sul campo standard")
    ap.add_argument("--apply", action="store_true", help="scrive (senza: dry-run)")
    args = ap.parse_args()

    contacts = fetch_all_contacts()
    plan = build_plan(contacts)

    mode = "APPLY — scrittura reale" if args.apply else "DRY-RUN — nessuna scrittura"
    print(f"\n{'═' * 74}\n  {mode}\n{'═' * 74}")

    print(f"\n{len(plan['scrivi'])} contatti senza sito sullo standard → lo ricevono:")
    for w in plan["scrivi"][:10]:
        print(f"   {w['email'][:38]:<40} ← {w['valore']!r}")
    if len(plan["scrivi"]) > 10:
        print(f"   … altri {len(plan['scrivi']) - 10}")

    print(f"\n{plan['invariati']} contatti hanno già lo stesso dominio: nulla da fare")

    print(f"\n{len(plan['conflitti'])} conflitti risolti automaticamente (standard sovrascritto):")
    for c in plan["conflitti"]:
        print(f"   {c['email'][:34]:<36} {c['standard']!r} → {c['custom']!r}\n      motivo: {c['motivo']}")

    print(f"\n{len(plan['da_decidere'])} conflitti NON risolti — restano come sono, decidili a mano:")
    for c in plan["da_decidere"]:
        print(f"   {c['email'][:34]:<36} standard={c['standard']!r}  custom={c['custom']!r}")

    if not args.apply:
        print(f"\n{'═' * 74}\nNessuna scrittura. Per applicare: --apply")
        return

    path = snapshot(contacts)
    print(f"\n💾 backup campo standard website: {path.relative_to(PROJECT_ROOT)}")

    n = 0
    for w in plan["scrivi"] + plan["conflitti"]:
        ghl.update_contact(w["id"], website=w.get("valore") or w["custom"])
        n += 1
        if n % 20 == 0:
            print(f"  … {n}")
        time.sleep(THROTTLE_S)
    print(f"\n✅ {n} contatti aggiornati sul campo standard `website`.")
    print("   Il custom 'Il tuo sito Web?' NON è stato toccato: va prima")
    print("   ripuntato il workflow GHL che lo usa (vedi workflows/ghl_field_hygiene.md).")


if __name__ == "__main__":
    try:
        main()
    except ghl.GHLError as exc:
        print(f"[website] ❌ errore GHL: {exc}", file=sys.stderr)
        sys.exit(1)
