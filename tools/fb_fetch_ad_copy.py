#!/usr/bin/env python3
"""Scarica i TESTI delle creative (primary text / headline / description / CTA / link)
di tutti gli annunci ATTIVI dell'ad account Meta configurato.

Riusa token e account da fb_ads_client (.env: FB_ACCESS_TOKEN, FB_AD_ACCOUNT_ID).

Uso:
  python tools/fb_fetch_ad_copy.py                # tutti gli annunci non-archiviati
  python tools/fb_fetch_ad_copy.py --active-only  # solo ACTIVE
  python tools/fb_fetch_ad_copy.py --json out.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fb_ads_client import ACCESS_TOKEN, GRAPH_BASE, _account_id, _configured  # noqa: E402


def _get(url: str, params: dict) -> dict:
    params = {**params, "access_token": ACCESS_TOKEN}
    r = requests.get(url, params=params, timeout=60)
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            msg = r.text[:200]
        raise SystemExit(f"❌ FB API {r.status_code}: {msg}")
    return r.json()


CREATIVE_FIELDS = (
    "title,body,object_story_spec,asset_feed_spec,call_to_action_type"
)


def fetch_ads(active_only: bool) -> list[dict]:
    """Lista leggera degli annunci (name, status, creative id), poi
    scarica ogni creative separatamente per non far esplodere l'API."""
    url = f"{GRAPH_BASE}/{_account_id()}/ads"
    params = {
        "fields": "name,status,effective_status,creative{id}",
        "limit": 50,
    }
    if active_only:
        params["effective_status"] = json.dumps(["ACTIVE"])
    ads: list[dict] = []
    data = _get(url, params)
    while True:
        ads.extend(data.get("data", []))
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        data = requests.get(nxt, timeout=60).json()

    # arricchisci ogni annuncio con la creative completa
    for ad in ads:
        cid = (ad.get("creative") or {}).get("id")
        if not cid:
            continue
        try:
            ad["creative"] = _get(f"{GRAPH_BASE}/{cid}", {"fields": CREATIVE_FIELDS})
        except SystemExit as e:
            ad["creative"] = {"_error": str(e)}
    return ads


def _extract(creative: dict) -> dict:
    """Estrae bodies/titles/descriptions/links da object_story_spec e asset_feed_spec."""
    res = {
        "bodies": [],
        "titles": [],
        "descriptions": [],
        "ctas": [],
        "links": [],
    }
    if not creative:
        return res

    # 1) campi diretti
    if creative.get("body"):
        res["bodies"].append(creative["body"])
    if creative.get("title"):
        res["titles"].append(creative["title"])
    if creative.get("call_to_action_type"):
        res["ctas"].append(creative["call_to_action_type"])

    # 2) object_story_spec (annuncio classico single)
    oss = creative.get("object_story_spec", {}) or {}
    for key in ("link_data", "video_data", "photo_data"):
        d = oss.get(key)
        if not d:
            continue
        if d.get("message"):
            res["bodies"].append(d["message"])
        if d.get("name"):
            res["titles"].append(d["name"])
        if d.get("description"):
            res["descriptions"].append(d["description"])
        if d.get("link"):
            res["links"].append(d["link"])
        cta = d.get("call_to_action", {}) or {}
        if cta.get("type"):
            res["ctas"].append(cta["type"])
        if cta.get("value", {}).get("link"):
            res["links"].append(cta["value"]["link"])

    # 3) asset_feed_spec (322 / dynamic: liste di testi e titoli)
    afs = creative.get("asset_feed_spec", {}) or {}
    for b in afs.get("bodies", []):
        if b.get("text"):
            res["bodies"].append(b["text"])
    for t in afs.get("titles", []):
        if t.get("text"):
            res["titles"].append(t["text"])
    for d in afs.get("descriptions", []):
        if d.get("text"):
            res["descriptions"].append(d["text"])
    for c in afs.get("call_to_action_types", []) or []:
        res["ctas"].append(c)
    for lk in afs.get("link_urls", []) or []:
        if lk.get("website_url"):
            res["links"].append(lk["website_url"])

    # dedup preservando ordine
    for k in res:
        seen = set()
        res[k] = [x for x in res[k] if not (x in seen or seen.add(x))]
    return res


def main() -> None:
    if not _configured():
        raise SystemExit("⚠️  FB_ACCESS_TOKEN / FB_AD_ACCOUNT_ID non configurati nel .env")

    active_only = "--active-only" in sys.argv
    json_out = None
    if "--json" in sys.argv:
        json_out = sys.argv[sys.argv.index("--json") + 1]

    ads = fetch_ads(active_only)
    ads.sort(key=lambda a: a.get("name", ""))

    parsed = []
    for ad in ads:
        info = _extract(ad.get("creative", {}))
        parsed.append({
            "name": ad.get("name"),
            "status": ad.get("status"),
            "effective_status": ad.get("effective_status"),
            **info,
        })

    if json_out:
        Path(json_out).write_text(json.dumps(parsed, ensure_ascii=False, indent=2))
        print(f"✅ Salvati {len(parsed)} annunci in {json_out}")

    # stampa leggibile
    for p in parsed:
        print("\n" + "=" * 70)
        print(f"📢 {p['name']}   [{p['effective_status']}]")
        for i, b in enumerate(p["bodies"], 1):
            print(f"\n  PRIMARY TEXT {i}:\n    " + b.replace("\n", "\n    "))
        for i, t in enumerate(p["titles"], 1):
            print(f"\n  HEADLINE {i}: {t}")
        for i, d in enumerate(p["descriptions"], 1):
            print(f"  DESCRIPTION {i}: {d}")
        if p["ctas"]:
            print(f"  CTA: {', '.join(p['ctas'])}")
        if p["links"]:
            print(f"  LINK: {', '.join(p['links'])}")


if __name__ == "__main__":
    main()
