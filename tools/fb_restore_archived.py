#!/usr/bin/env python3
"""
Ripristina da ARCHIVED a PAUSED su Meta.

Contesto: il 17/07/2026 quattro campagne/adset di ads-2 sono state archiviate
tra le 13:49 e le 13:51. L'archiviazione è reversibile: gli oggetti esistono,
sono solo nascosti dai filtri di default di Ads Manager e della Graph API.

Due scelte deliberate:

1. ARCHIVED → PAUSED, mai → ACTIVE. Riattivare significa far ripartire la spesa:
   quella decisione resta umana. Il tool rende le cose di nuovo visibili e
   modificabili, niente di più.

2. Filtro temporale obbligatorio (--since). Ripristinare tutto ciò che è
   archiviato resusciterebbe anche ciò che era stato archiviato apposta mesi
   fa. Si ripristina solo la finestra dell'incidente.

L'ordine conta: campagna → adset → ads. Un'adset dentro una campagna archiviata
resta comunque non deliverabile.

CLI:
  python tools/fb_restore_archived.py list  --account act_X --since 2026-07-17T13:00
  python tools/fb_restore_archived.py apply --account act_X --since 2026-07-17T13:00
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_creative_tracker import BASE, TOKEN, _paginate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

LEVELS = ("campaigns", "adsets", "ads")   # ordine di ripristino: dall'alto in giù


def _post(node: str, data: dict) -> dict:
    data = dict(data, access_token=TOKEN)
    r = requests.post(f"{BASE}/{node}", data=data, timeout=30)
    out = r.json()
    if "error" in out:
        raise RuntimeError(out["error"].get("message", str(out["error"])))
    return out


def _parse_since(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"--since non valido: {s!r} (atteso es. 2026-07-17T13:00)")


def find_archived(account: str, since: datetime,
                  until: datetime | None = None) -> dict[str, list[dict]]:
    """Oggetti archiviati nella finestra [since, until], per livello.

    `until` esiste perché archiviazioni diverse possono avere cause diverse:
    ripristinare in blocco tutto ciò che è archiviato oggi rimetterebbe in piedi
    anche ciò che è stato archiviato di proposito un'ora dopo l'incidente.
    """
    found: dict[str, list[dict]] = {}
    for level in LEVELS:
        rows = _paginate(f"{BASE}/{account}/{level}", {
            "fields": "id,name,status,effective_status,updated_time",
            "effective_status": json.dumps(["ARCHIVED"]),
            "limit": 300,
        })
        keep = []
        for r in rows:
            ts = r.get("updated_time", "")
            try:
                when = datetime.fromisoformat(ts).replace(tzinfo=None)
            except ValueError:
                continue
            if when >= since and (until is None or when <= until):
                r["_when"] = when
                keep.append(r)
        found[level] = sorted(keep, key=lambda x: x["_when"])
    return found


def show(found: dict[str, list[dict]], since: datetime, until: datetime | None = None) -> int:
    total = sum(len(v) for v in found.values())
    finestra = (f"fra {since:%Y-%m-%d %H:%M} e {until:%H:%M}" if until
                else f"dopo {since:%Y-%m-%d %H:%M}")
    print(f"Archiviati {finestra} — {total} oggetti\n")
    for level in LEVELS:
        rows = found[level]
        print(f"{level.upper()} ({len(rows)})")
        for r in rows[:12]:
            print(f"  {r['_when']:%H:%M:%S}  {r['id'][:18]}  {(r.get('name') or '')[:44]}")
        if len(rows) > 12:
            print(f"  … e altri {len(rows) - 12}")
        print()
    return total


def apply(found: dict[str, list[dict]]) -> tuple[int, int]:
    ok = fail = 0
    for level in LEVELS:   # campagne prima: un'adset sotto campagna archiviata non rivive
        rows = found[level]
        if not rows:
            continue
        print(f"\n▸ {level} ({len(rows)})")
        for r in rows:
            try:
                _post(r["id"], {"status": "PAUSED"})
                ok += 1
                print(f"  ✓ {(r.get('name') or r['id'])[:48]:<50} ARCHIVED → PAUSED")
            except Exception as e:
                fail += 1
                print(f"  ✗ {(r.get('name') or r['id'])[:48]:<50} {str(e)[:60]}")
    return ok, fail


def verify(account: str, found: dict[str, list[dict]]) -> None:
    """Rileggere lo stato da Meta: l'unica prova che il ripristino è reale."""
    print("\n=== VERIFICA (riletta da Meta) ===")
    for level in LEVELS:
        ids = [r["id"] for r in found[level]]
        if not ids:
            continue
        still = 0
        for i in ids:
            try:
                d = requests.get(f"{BASE}/{i}", params={"fields": "status",
                                                        "access_token": TOKEN}, timeout=30).json()
                if d.get("status") == "ARCHIVED":
                    still += 1
            except Exception:
                still += 1
        print(f"  {level:<10} {len(ids) - still}/{len(ids)} ora PAUSED"
              + (f"  ⚠️ {still} ancora archiviati" if still else ""))


def main() -> int:
    p = argparse.ArgumentParser(description="Ripristina ARCHIVED → PAUSED su Meta")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("list", "apply"):
        s = sub.add_parser(name)
        s.add_argument("--account", required=True)
        s.add_argument("--since", required=True,
                       help="ISO, es. 2026-07-17T13:00 — si ripristina solo da qui in poi")
        s.add_argument("--until", help="ISO: limite superiore della finestra")
    a = p.parse_args()

    since = _parse_since(a.since)
    until = _parse_since(a.until) if a.until else None
    if since > datetime.now():
        raise SystemExit("--since è nel futuro: non troverei nulla")
    if since < datetime.now() - timedelta(days=7):
        print(f"⚠️  --since è {(datetime.now()-since).days} giorni fa: rischi di "
              f"ripristinare cose archiviate di proposito. Controlla la lista.\n")

    found = find_archived(a.account, since, until)
    total = show(found, since, until)
    if total == 0:
        print("Niente da ripristinare in questa finestra.")
        return 0
    if a.cmd == "list":
        print("Nessuna modifica fatta. Per applicare: stesso comando con `apply`.")
        return 0

    ok, fail = apply(found)
    verify(a.account, found)
    print(f"\n{ok} ripristinati a PAUSED, {fail} falliti.")
    print("Sono PAUSED, non ACTIVE: non spendono. La riattivazione la decidi tu.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
