#!/usr/bin/env python3
"""PIANO INIZIALE — bozza PAUSED, NO DCO.
  1 campagna CBO €31/gg (OUTCOME_LEADS)
   └─ 1 adset (normale, NON dynamic)
       ├─ Ad img 1  · gialla   → copy B1 + headline T1
       ├─ Ad img 2  · secchio  → copy B1 + headline T1   (copy fisso, vario solo l'immagine)
       ├─ Ad img 3  · numero   → copy B1 + headline T1
       ├─ Ad video  · talking head → copy B1 + headline T1
       └─ Ad controllo · gialla con copy ATTUALE
Tutte AD SINGOLE (1 immagine/video + 1 testo + 1 headline). Niente dynamic creative.
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
DELETE_CAMPAIGN = "120249093445790535"  # bozza DCO sbagliata da rimuovere

GIALLA = "918a547044ff14dedf432415aedba365"
SECCHIO = "304444ec5a10f23afb670bd93cf41d72"
NUMERO = "c9ac5900c8cf6b3e05210feaa1224cf7"
VIDEO_ID = "970089952661153"
VIDEO_THUMB = "6a126a5eb41ff34dc16c7771eff20d65"

B1 = ("Fatturi più di 20k€/mese e la tua email si limita a qualche newsletter? "
      "Stai lasciando a terra 5-7k€ ogni mese.\n"
      "Non è traffico che ti manca: sono i flussi che non hai o che non funzionano — "
      "carrello abbandonato, post-acquisto, win-back.\n"
      "Quei soldi sono già nella tua lista. Vanno solo recuperati.\n"
      "Fai il test gratuito e scopri quanto stai perdendo 👇")
T1 = "Scopri il tuo potenziale email in 2 minuti"
DESC = "Analisi gratuita per chi fattura 20K+/mese"

C_MSG = ("Fatturi più di 20k€/mese e la tua email si limita a qualche newsletter ogni tanto? "
         "Stai lasciando a terra 5-7k€ ogni mese.\n"
         "Non è traffico che ti manca. Sono i flussi che non hai o che non funzionano: "
         "carrello abbandonato, post-acquisto, win-back.\n"
         "Quei soldi sono già nella tua lista. Vanno solo recuperati.\n"
         "Fai il test gratuito e scopri quanto stai perdendo 👇")


def post(path, data):
    data = {**data, "access_token": ACCESS_TOKEN}
    r = requests.post(f"{GRAPH_BASE}/{path}", data=data, timeout=60)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {json.dumps(j.get('error', j), ensure_ascii=False)[:400]}")
    return j


def delete(oid):
    r = requests.delete(f"{GRAPH_BASE}/{oid}", params={"access_token": ACCESS_TOKEN}, timeout=60)
    return r.status_code, r.text[:120]


def img_creative(name, image_hash, message, headline):
    return post(f"{ACC}/adcreatives", {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": PAGE_ID,
            "link_data": {
                "image_hash": image_hash,
                "link": LINK,
                "message": message,
                "name": headline,
                "description": DESC,
                "call_to_action": {"type": CTA, "value": {"link": LINK}},
            },
        }),
    })


def video_creative(name, message, headline):
    return post(f"{ACC}/adcreatives", {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": PAGE_ID,
            "video_data": {
                "video_id": VIDEO_ID,
                "image_hash": VIDEO_THUMB,
                "message": message,
                "title": headline,
                "link_description": DESC,
                "call_to_action": {"type": CTA, "value": {"link": LINK}},
            },
        }),
    })


def main():
    cfg = json.load(open(".tmp/322_source_config.json"))
    targeting = cfg["targeting"]
    state = {"ads": []}

    if DELETE_CAMPAIGN:
        print("⌫ cancello bozza DCO sbagliata…", delete(DELETE_CAMPAIGN))

    print("① Campagna CBO PAUSED €31/gg…")
    camp = post(f"{ACC}/campaigns", {
        "name": "AND1 · 322 Loss Aversion — DRAFT",
        "objective": "OUTCOME_LEADS",
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
        "daily_budget": 3100,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    })
    state["campaign_id"] = camp["id"]
    print("   ✅", camp["id"])

    print("② Adset PAUSED (normale, NO DCO)…")
    adset = post(f"{ACC}/adsets", {
        "name": "IT — eCommerce Owner — Broad",
        "campaign_id": camp["id"],
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "promoted_object": json.dumps({"pixel_id": PIXEL_ID, "custom_event_type": "COMPLETE_REGISTRATION"}),
        "targeting": json.dumps(targeting),
        "status": "PAUSED",
    })
    state["adset_id"] = adset["id"]
    print("   ✅", adset["id"])

    def make_ad(name, creative):
        ad = post(f"{ACC}/ads", {
            "name": name, "adset_id": adset["id"],
            "creative": json.dumps({"creative_id": creative["id"]}), "status": "PAUSED",
        })
        print(f"   ✅ {name}: ad {ad['id']}")
        state["ads"].append({"name": name, "ad_id": ad["id"], "creative_id": creative["id"]})

    print("③ Ad singole (copy fisso, vario solo l'immagine)…")
    make_ad("IMG 1 · Gialla",  img_creative("IMG Gialla",  GIALLA,  B1, T1))
    make_ad("IMG 2 · Secchio", img_creative("IMG Secchio", SECCHIO, B1, T1))
    make_ad("IMG 3 · Numero",  img_creative("IMG Numero",  NUMERO,  B1, T1))
    make_ad("VIDEO · Talking Head", video_creative("VIDEO Talking Head", B1, T1))
    make_ad("CONTROLLO · Gialla (copy attuale)", img_creative("CTRL Gialla", GIALLA, C_MSG, T1))

    json.dump(state, open(".tmp/322_single_state.json", "w"), indent=2)
    print("\n✅ FATTO — tutto PAUSED.")
    print(f"Campaign: {state['campaign_id']}  |  Adset: {state['adset_id']}")
    print(f"Adsmanager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2390793521074673&selected_campaign_ids={state['campaign_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}")
        sys.exit(1)
