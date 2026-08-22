#!/usr/bin/env python3
"""Crea una BOZZA (tutto PAUSED) della struttura Andromeda 1 / 322 sull'account
target, clonando le impostazioni dell'adset live "IT — eCommerce Owner — Broad".

Struttura creata:
  Campagna PAUSED (OUTCOME_LEADS)
   └─ 1 adset PAUSED €31/gg (targeting/pixel/evento clonati)
      ├─ Ad A — 322 immagini (3 img loss-aversion + 2 testi + 2 headline)  [dynamic creative]
      ├─ Ad B — video talking head (stesso 2 testi + 2 headline)          [dynamic creative]
      └─ Ad C — controllo: gialla singola con copy attuale

NON pubblica nulla: ogni oggetto nasce in status PAUSED.
"""
from __future__ import annotations
import sys, json
sys.path.insert(0, "tools")
from fb_ads_client import ACCESS_TOKEN, GRAPH_BASE
import requests

ACC = "act_2390793521074673"
PAGE_ID = "101236142286783"
PIXEL_ID = "1142953766808623"
LINK = "https://mailift.com/optin-calcolatore-page"
CTA = "SEE_DETAILS"

# --- asset esistenti (image_hash / video_id verificati dall'account) ---
IMG_GIALLA = "918a547044ff14dedf432415aedba365"   # brutta forte / loss aversion
IMG_SECCHIO = "304444ec5a10f23afb670bd93cf41d72"  # 01 secchio bucato
IMG_NUMERO = "c9ac5900c8cf6b3e05210feaa1224cf7"   # 14 numero preciso
VIDEO_ID = "970089952661153"                       # talking head
VIDEO_THUMB = "6a126a5eb41ff34dc16c7771eff20d65"

# --- copy condiviso A + B ---
B1 = ("Fatturi più di 20k€/mese e la tua email si limita a qualche newsletter? "
      "Stai lasciando a terra 5-7k€ ogni mese.\n"
      "Non è traffico che ti manca: sono i flussi che non hai o che non funzionano — "
      "carrello abbandonato, post-acquisto, win-back.\n"
      "Quei soldi sono già nella tua lista. Vanno solo recuperati.\n"
      "Fai il test gratuito e scopri quanto stai perdendo 👇")
B2 = ("Il tuo eCommerce ha un problema che le ads non risolveranno mai.\n"
      "Ogni euro che spendi in Meta porta traffico dentro. Ma senza una macchina di "
      "retention, quei clienti escono dalla porta sul retro.\n"
      "Welcome flow assente. Carrello abbandonato senza follow-up. Nessuna sequenza "
      "post-acquisto. Nessun win-back.\n"
      "Scopri esattamente quanto stai perdendo ogni mese. Analisi gratuita, risultati in 48h 👇")
T1 = "Scopri il tuo potenziale email in 2 minuti"
T2 = "Il tuo eCom è un secchio bucato?"
DESC = "Analisi gratuita per chi fattura 20K+/mese"

# --- copy controllo (gialla attuale) ---
C_MSG = ("Fatturi più di 20k€/mese e la tua email si limita a qualche newsletter ogni tanto? "
         "Stai lasciando a terra 5-7k€ ogni mese.\n"
         "Non è traffico che ti manca. Sono i flussi che non hai o che non funzionano: "
         "carrello abbandonato, post-acquisto, win-back.\n"
         "Quei soldi sono già nella tua lista. Vanno solo recuperati.\n"
         "Fai il test gratuito e scopri quanto stai perdendo 👇")


def post(path: str, data: dict) -> dict:
    data = {**data, "access_token": ACCESS_TOKEN}
    r = requests.post(f"{GRAPH_BASE}/{path}", data=data, timeout=60)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {json.dumps(j.get('error', j), ensure_ascii=False)[:400]}")
    return j


def main():
    cfg = json.load(open(".tmp/322_source_config.json"))
    targeting = cfg["targeting"]
    state = {}

    print("① Campagna PAUSED…")
    camp = post(f"{ACC}/campaigns", {
        "name": "AND1 · 322 Loss Aversion — DRAFT",
        "objective": "OUTCOME_LEADS",
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
        "is_adset_budget_sharing_enabled": "false",
    })
    state["campaign_id"] = camp["id"]
    print("   ✅", camp["id"])

    print("② Adset PAUSED €31/gg (clone)…")
    adset_payload = {
        "name": "IT — eCommerce Owner — Broad (322 test)",
        "campaign_id": camp["id"],
        "daily_budget": 3100,
        "billing_event": "IMPRESSIONS",
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "promoted_object": json.dumps({"pixel_id": PIXEL_ID, "custom_event_type": "COMPLETE_REGISTRATION"}),
        "targeting": json.dumps(targeting),
        "status": "PAUSED",
    }
    adset = post(f"{ACC}/adsets", adset_payload)
    state["adset_id"] = adset["id"]
    print("   ✅", adset["id"])

    def make_ad(name, creative_spec):
        cr = post(f"{ACC}/adcreatives", {"name": f"{name} — creative", **creative_spec})
        ad = post(f"{ACC}/ads", {
            "name": name,
            "adset_id": adset["id"],
            "creative": json.dumps({"creative_id": cr["id"]}),
            "status": "PAUSED",
        })
        print(f"   ✅ {name}: ad {ad['id']} / creative {cr['id']}")
        return {"ad_id": ad["id"], "creative_id": cr["id"]}

    print("③ Ad A — 322 immagini (dynamic creative)…")
    afs_img = {
        "images": [{"hash": IMG_GIALLA}, {"hash": IMG_SECCHIO}, {"hash": IMG_NUMERO}],
        "bodies": [{"text": B1}, {"text": B2}],
        "titles": [{"text": T1}, {"text": T2}],
        "descriptions": [{"text": DESC}],
        "ad_formats": ["SINGLE_IMAGE"],
        "call_to_action_types": [CTA],
        "link_urls": [{"website_url": LINK}],
    }
    state["ad_A"] = make_ad("A · 322 Loss Aversion (img)", {
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec": json.dumps(afs_img),
    })

    print("④ Ad B — video talking head (dynamic creative)…")
    afs_vid = {
        "videos": [{"video_id": VIDEO_ID, "thumbnail_hash": VIDEO_THUMB}],
        "bodies": [{"text": B1}, {"text": B2}],
        "titles": [{"text": T1}, {"text": T2}],
        "descriptions": [{"text": DESC}],
        "ad_formats": ["SINGLE_VIDEO"],
        "call_to_action_types": [CTA],
        "link_urls": [{"website_url": LINK}],
    }
    state["ad_B"] = make_ad("B · Talking Head (video)", {
        "object_story_spec": json.dumps({"page_id": PAGE_ID}),
        "asset_feed_spec": json.dumps(afs_vid),
    })

    print("⑤ Ad C — controllo gialla singola…")
    oss_ctrl = {
        "page_id": PAGE_ID,
        "link_data": {
            "image_hash": IMG_GIALLA,
            "link": LINK,
            "message": C_MSG,
            "name": T1,
            "description": DESC,
            "call_to_action": {"type": CTA, "value": {"link": LINK}},
        },
    }
    state["ad_C"] = make_ad("C · Controllo Gialla", {
        "object_story_spec": json.dumps(oss_ctrl),
    })

    json.dump(state, open(".tmp/322_draft_state.json", "w"), indent=2)
    print("\n✅ FATTO — tutto PAUSED. Stato salvato in .tmp/322_draft_state.json")
    print(f"Campaign: {state['campaign_id']}")
    print(f"Adsmanager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2390793521074673&selected_campaign_ids={state['campaign_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}")
        try:
            json.dump({"error": str(e)}, open(".tmp/322_draft_error.json", "w"))
        except Exception:
            pass
        sys.exit(1)
