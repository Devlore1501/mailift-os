#!/usr/bin/env python3
"""Bozza PAUSED — CBO con 3 adset DIVERSI, ad singole (NO DCO).
  Campagna CBO €31/gg (OUTCOME_LEADS)
   ├─ Adset 1 · Immagini Loss Aversion → 3 ad singole (gialla, secchio, numero) — copy fisso B1 + headline T1
   ├─ Adset 2 · Video                  → 1 ad singola (talking head) — B1 + T1
   └─ Adset 3 · Controllo              → 1 ad singola (gialla, copy ATTUALE)
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
DELETE_CAMPAIGN = "120249093570210535"  # bozza a 1 adset da rimuovere

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


def make_adset(campaign_id, name, targeting):
    return post(f"{ACC}/adsets", {
        "name": name, "campaign_id": campaign_id,
        "billing_event": "IMPRESSIONS", "optimization_goal": "OFFSITE_CONVERSIONS",
        "promoted_object": json.dumps({"pixel_id": PIXEL_ID, "custom_event_type": "COMPLETE_REGISTRATION"}),
        "targeting": json.dumps(targeting), "status": "PAUSED",
    })


def img_creative(name, image_hash, message, headline):
    return post(f"{ACC}/adcreatives", {"name": name, "object_story_spec": json.dumps({
        "page_id": PAGE_ID, "link_data": {
            "image_hash": image_hash, "link": LINK, "message": message,
            "name": headline, "description": DESC,
            "call_to_action": {"type": CTA, "value": {"link": LINK}}}})})


def video_creative(name, message, headline):
    return post(f"{ACC}/adcreatives", {"name": name, "object_story_spec": json.dumps({
        "page_id": PAGE_ID, "video_data": {
            "video_id": VIDEO_ID, "image_hash": VIDEO_THUMB, "message": message,
            "title": headline, "link_description": DESC,
            "call_to_action": {"type": CTA, "value": {"link": LINK}}}})})


def main():
    cfg = json.load(open(".tmp/322_source_config.json"))
    tg = cfg["targeting"]
    state = {"adsets": {}}

    if DELETE_CAMPAIGN:
        print("⌫ cancello bozza a 1 adset…", delete(DELETE_CAMPAIGN))

    print("① Campagna CBO PAUSED €31/gg…")
    camp = post(f"{ACC}/campaigns", {
        "name": "AND1 · 322 Loss Aversion (CBO) — DRAFT", "objective": "OUTCOME_LEADS",
        "status": "PAUSED", "special_ad_categories": json.dumps([]),
        "daily_budget": 3100, "bid_strategy": "LOWEST_COST_WITHOUT_CAP"})
    state["campaign_id"] = camp["id"]
    print("   ✅", camp["id"])

    def add_ad(adset_id, name, creative):
        ad = post(f"{ACC}/ads", {"name": name, "adset_id": adset_id,
                                 "creative": json.dumps({"creative_id": creative["id"]}), "status": "PAUSED"})
        print(f"      ✅ {name}: ad {ad['id']}")
        return ad["id"]

    # Adset 1 — immagini
    print("② Adset 1 · Immagini Loss Aversion…")
    as1 = make_adset(camp["id"], "1 · Immagini Loss Aversion", tg)
    print("   ✅ adset", as1["id"])
    ads1 = [
        add_ad(as1["id"], "Gialla",  img_creative("IMG Gialla",  GIALLA,  B1, T1)),
        add_ad(as1["id"], "Secchio", img_creative("IMG Secchio", SECCHIO, B1, T1)),
        add_ad(as1["id"], "Numero",  img_creative("IMG Numero",  NUMERO,  B1, T1)),
    ]
    state["adsets"]["immagini"] = {"adset_id": as1["id"], "ads": ads1}

    # Adset 2 — video
    print("③ Adset 2 · Video…")
    as2 = make_adset(camp["id"], "2 · Video Talking Head", tg)
    print("   ✅ adset", as2["id"])
    state["adsets"]["video"] = {"adset_id": as2["id"],
        "ads": [add_ad(as2["id"], "Talking Head", video_creative("VIDEO Talking Head", B1, T1))]}

    # Adset 3 — controllo
    print("④ Adset 3 · Controllo…")
    as3 = make_adset(camp["id"], "3 · Controllo (gialla copy attuale)", tg)
    print("   ✅ adset", as3["id"])
    state["adsets"]["controllo"] = {"adset_id": as3["id"],
        "ads": [add_ad(as3["id"], "Controllo Gialla", img_creative("CTRL Gialla", GIALLA, C_MSG, T1))]}

    json.dump(state, open(".tmp/322_cbo3_state.json", "w"), indent=2)
    print("\n✅ FATTO — tutto PAUSED.")
    print(f"Campaign: {state['campaign_id']}")
    print(f"Adsmanager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2390793521074673&selected_campaign_ids={state['campaign_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}")
        sys.exit(1)
