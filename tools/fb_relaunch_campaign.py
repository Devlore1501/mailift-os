#!/usr/bin/env python3
"""
Ricostruisce e rilancia la campagna ads-2 cancellata il 17/07/2026.

Perché ricostruire e non "ripristinare": campagna, adset e ads erano DELETED,
non solo archiviate. Meta non permette di riattivare oggetti cancellati
("you can only edit the name") e il deep_copy di una campagna con figli
cancellati produce un guscio vuoto. L'unica strada fedele è:

  1. creare una campagna nuova con la stessa config
  2. creare un adset nuovo con lo stesso targeting/budget/ottimizzazione
  3. COPIARE dentro le 20 ads cancellate (le creative esistono ancora, quindi
     l'annuncio resta identico all'originale)

Sicurezza:
- build   → crea tutto in PAUSA e verifica. Nessuna spesa.
- publish → mette ACTIVE campagna+adset+ads. Solo dopo che build ha confermato
            che le 20 ads sono dentro. Da qui parte la spesa.

Config replicata (letta dagli oggetti cancellati, ancora leggibili via API):
  campagna: OUTCOME_LEADS, AUCTION, budget a livello adset
  adset:    IT — eCommerce Owner — Broad · €31/giorno · optimization VALUE ·
            pixel 1142953766808623 · evento COMPLETE_REGISTRATION · geo IT ·
            18-65 · Advantage+ · schedule 31 giorni
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

TOKEN = __import__("os").environ["FB_ACCESS_TOKEN"]
API = "https://graph.facebook.com/v21.0"
ACCOUNT = "act_2390793521074673"

# Oggetti originali cancellati — la fonte da cui leggere config e ads.
SRC_CAMPAIGN = "120249057169080535"   # 🎨 Immagini Statiche — Bozze Luglio 2026
SRC_ADSET = "120249057169070535"      # IT — eCommerce Owner — Broad
RUN_DAYS = 31

STATE_FILE = ROOT / ".tmp" / "relaunch_state.json"


def _get(node: str, fields: str, extra: dict | None = None) -> dict:
    p = {"fields": fields, "access_token": TOKEN}
    if extra:
        p.update(extra)
    r = requests.get(f"{API}/{node}", params=p, timeout=60)
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"GET {node}: {d['error'].get('error_user_msg') or d['error']['message']}")
    return d


def _post(node: str, data: dict) -> dict:
    data = dict(data, access_token=TOKEN)
    r = requests.post(f"{API}/{node}", data=data, timeout=120)
    d = r.json()
    if "error" in d:
        e = d["error"]
        raise RuntimeError(f"POST {node}: {e.get('error_user_msg') or e.get('message')}")
    return d


def _paginate(node: str, params: dict) -> list[dict]:
    params = dict(params, access_token=TOKEN)
    out, url, p = [], f"{API}/{node}", params
    while True:
        r = requests.get(url, params=p, timeout=60).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message"))
        out.extend(r.get("data", []))
        nxt = r.get("paging", {}).get("next")
        if not nxt:
            return out
        url, p = nxt, {}


def _save_state(s: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2))


def _load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


# ── build ─────────────────────────────────────────────────────────────────────

def build() -> int:
    # Config sorgente
    camp = _get(SRC_CAMPAIGN, "name,objective,buying_type,special_ad_categories")
    aset = _get(SRC_ADSET, ("name,daily_budget,lifetime_budget,billing_event,optimization_goal,"
                            "bid_strategy,destination_type,promoted_object,targeting"))
    src_ads = _paginate(f"{SRC_ADSET}/ads", {
        "fields": "id,name", "effective_status": json.dumps(["ARCHIVED"]), "limit": 100})
    if not src_ads:
        print("✗ nessuna ad sorgente trovata — interrompo per non creare un adset vuoto")
        return 1

    name = camp["name"].replace(" - Copy", "")
    print(f"Ricostruisco: {name}")
    print(f"  {len(src_ads)} ads · adset '{aset['name']}' · "
          f"€{int(aset['daily_budget'])/100:.0f}/giorno · {RUN_DAYS} giorni")

    # 1. campagna (PAUSED)
    new_camp = _post(f"{ACCOUNT}/campaigns", {
        "name": f"{name} (rilancio 17/07)",
        "objective": camp["objective"],
        "buying_type": camp.get("buying_type", "AUCTION"),
        "special_ad_categories": json.dumps(camp.get("special_ad_categories") or []),
        # Budget sull'adset (come l'originale), non sulla campagna: niente CBO.
        "is_adset_budget_sharing_enabled": "false",
        "status": "PAUSED",
    })["id"]
    print(f"  ✓ campagna creata {new_camp}")

    # 2. adset (PAUSED), schedule 31 giorni da ora
    start = datetime.now(timezone.utc) + timedelta(minutes=5)
    end = start + timedelta(days=RUN_DAYS)
    adset_payload = {
        "name": aset["name"],
        "campaign_id": new_camp,
        "daily_budget": aset["daily_budget"],
        "billing_event": aset["billing_event"],
        "optimization_goal": aset["optimization_goal"],
        "bid_strategy": aset.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP"),
        "promoted_object": json.dumps(aset["promoted_object"]),
        "targeting": json.dumps(aset["targeting"]),
        "start_time": start.isoformat(timespec="seconds"),
        "end_time": end.isoformat(timespec="seconds"),
        "status": "PAUSED",
    }
    if aset.get("destination_type") and aset["destination_type"] != "UNDEFINED":
        adset_payload["destination_type"] = aset["destination_type"]
    new_adset = _post(f"{ACCOUNT}/adsets", adset_payload)["id"]
    print(f"  ✓ adset creato {new_adset} · schedule {start:%d/%m %H:%M} → {end:%d/%m %H:%M}")

    # 3. copia le 20 ads nel nuovo adset (PAUSED). /copies preserva la creative.
    copied, failed = [], []
    for a in src_ads:
        try:
            res = _post(f"{a['id']}/copies", {
                "adset_id": new_adset,
                "status_option": "PAUSED",
            })
            copied.append({"src": a["id"], "name": a["name"], "new": res.get("copied_ad_id") or res.get("ad_id")})
            print(f"    ✓ {a['name'][:34]}")
        except Exception as e:
            failed.append({"name": a["name"], "err": str(e)[:70]})
            print(f"    ✗ {a['name'][:34]}  {str(e)[:60]}")
        time.sleep(0.4)

    state = {"campaign": new_camp, "adset": new_adset, "name": name,
             "copied": copied, "failed": failed,
             "start": start.isoformat(), "end": end.isoformat(),
             "daily_budget_cents": aset["daily_budget"]}
    _save_state(state)

    print(f"\n{len(copied)}/{len(src_ads)} ads copiate, {len(failed)} fallite. Tutto in PAUSA.")
    _report_verify(new_adset, len(src_ads))
    daily = int(aset["daily_budget"]) / 100
    print(f"\nSpesa massima prevista: €{daily:.0f}/giorno × {RUN_DAYS} giorni = ~€{daily*RUN_DAYS:.0f}")
    print("Niente è ancora online. Per pubblicare: python tools/fb_relaunch_campaign.py publish")
    return 1 if failed else 0


def _report_verify(adset: str, expected: int) -> None:
    ads = _paginate(f"{adset}/ads", {"fields": "id,name,effective_status", "limit": 100})
    print(f"\n=== VERIFICA (riletta da Meta) ===")
    print(f"  ads nel nuovo adset: {len(ads)}/{expected}")
    bad = [a for a in ads if a.get("effective_status") not in ("PAUSED", "PENDING_REVIEW", "ADSET_PAUSED", "CAMPAIGN_PAUSED")]
    if bad:
        print(f"  ⚠️ {len(bad)} ads in stato inatteso: {[a['effective_status'] for a in bad][:5]}")


# ── publish ───────────────────────────────────────────────────────────────────

def publish() -> int:
    s = _load_state()
    if not s.get("campaign"):
        print("Nessuna campagna costruita. Lancia prima: build")
        return 1

    ads = _paginate(f"{s['adset']}/ads", {"fields": "id,name,effective_status", "limit": 100})
    if not ads:
        print("✗ il nuovo adset non contiene ads — non pubblico un adset vuoto")
        return 1

    daily = int(s["daily_budget_cents"]) / 100
    print(f"Pubblico: {s['name']} (rilancio)")
    print(f"  {len(ads)} ads · €{daily:.0f}/giorno · fino al "
          f"{datetime.fromisoformat(s['end']):%d/%m/%Y}")
    print(f"  spesa massima: ~€{daily * RUN_DAYS:.0f}")

    # Ordine: ads → adset → campagna. Attivo i figli prima del padre così quando
    # la campagna si accende è già tutto pronto a erogare.
    ok = 0
    for a in ads:
        try:
            _post(a["id"], {"status": "ACTIVE"})
            ok += 1
        except Exception as e:
            print(f"  ✗ ad {a['name'][:30]}: {str(e)[:50]}")
    print(f"  ✓ {ok}/{len(ads)} ads ACTIVE")
    _post(s["adset"], {"status": "ACTIVE"})
    print("  ✓ adset ACTIVE")
    _post(s["campaign"], {"status": "ACTIVE"})
    print("  ✓ campagna ACTIVE")

    # Verifica finale rileggendo da Meta
    c = _get(s["campaign"], "name,effective_status")
    print(f"\n=== ONLINE ===")
    print(f"  {c['name']} · stato: {c['effective_status']}")
    print(f"  https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={ACCOUNT.replace('act_','')}")
    print("  Le ads passano da 'In revisione' ad 'Attiva' dopo l'approvazione di Meta (di solito <1h).")
    return 0


def recreate() -> int:
    """Ricrea le 20 ads da ZERO nell'adset già esistente.

    Perché non copiare: copiare un'ad cancellata produce una copia anch'essa
    nata ARCHIVED e non modificabile (stesso PostProcessing dell'originale).
    L'unica via che dà ads erogabili è creare creative e ads nuove dalla spec
    dell'originale — l'image_hash è dello stesso account, quindi le immagini
    sono le stesse, byte per byte.
    """
    s = _load_state()
    if not s.get("adset"):
        print("Nessun adset. Lancia prima: build")
        return 1

    # Le sorgenti: nome ad → creative_id originale (ancora leggibile).
    src_ads = _paginate(f"{SRC_ADSET}/ads", {
        "fields": "name,creative{id}", "effective_status": json.dumps(["ARCHIVED"]), "limit": 100})
    print(f"Ricreo {len(src_ads)} ads da zero nell'adset {s['adset']}")

    made, failed = [], []
    for a in sorted(src_ads, key=lambda x: x["name"]):
        cid = (a.get("creative") or {}).get("id")
        try:
            spec = _get(cid, "object_story_spec")["object_story_spec"]
            ld = spec.get("link_data", {})
            # Creative nuova dalla stessa link_data (stesso image_hash).
            new_creative = _post(f"{ACCOUNT}/adcreatives", {
                "name": f"{a['name']} (rilancio)",
                "object_story_spec": json.dumps({
                    "page_id": spec.get("page_id"),
                    "link_data": {
                        "link": ld.get("link"),
                        "message": ld.get("message"),
                        "name": ld.get("name"),
                        "description": ld.get("description"),
                        "image_hash": ld.get("image_hash"),
                        "call_to_action": ld.get("call_to_action"),
                    },
                }),
            })["id"]
            new_ad = _post(f"{ACCOUNT}/ads", {
                "name": a["name"].replace(" - Copy", ""),
                "adset_id": s["adset"],
                "creative": json.dumps({"creative_id": new_creative}),
                "status": "ACTIVE",
            })["id"]
            made.append({"name": a["name"], "ad": new_ad})
            print(f"  ✓ {a['name'][:34]}")
        except Exception as e:
            failed.append({"name": a["name"], "err": str(e)[:70]})
            print(f"  ✗ {a['name'][:34]}  {str(e)[:60]}")
        time.sleep(0.4)

    s["recreated"] = made
    s["recreate_failed"] = failed
    _save_state(s)
    print(f"\n{len(made)}/{len(src_ads)} ads ricreate ATTIVE, {len(failed)} fallite.")
    return 1 if failed else 0


def status() -> int:
    s = _load_state()
    if not s.get("campaign"):
        print("Nessuna campagna costruita.")
        return 0
    c = _get(s["campaign"], "name,effective_status")
    ads = _paginate(f"{s['adset']}/ads", {"fields": "effective_status", "limit": 100})
    from collections import Counter
    print(f"{c['name']} — {c['effective_status']}")
    print(f"  {len(ads)} ads: {dict(Counter(a['effective_status'] for a in ads))}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Rilancia la campagna ads-2 cancellata")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="ricostruisci campagna+adset (le copie ads sono un vicolo cieco)")
    sub.add_parser("recreate", help="ricrea le 20 ads da zero, ATTIVE")
    sub.add_parser("publish", help="metti ONLINE (da qui parte la spesa)")
    sub.add_parser("status")
    a = p.parse_args()
    if a.cmd == "build":
        return build()
    if a.cmd == "recreate":
        return recreate()
    if a.cmd == "publish":
        return publish()
    if a.cmd == "status":
        return status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
