#!/usr/bin/env python3
"""Bozza (PAUSED) struttura 322 su CBO:
  1 campagna CBO (budget €31/gg a livello campagna, OUTCOME_LEADS)
   ├─ Adset 1 (Dynamic Creative) → 1 ad 322 = 3 immagini + 2 copy + 2 headline
   ├─ Adset 2 (Dynamic Creative) → stesso 322
   └─ Adset 3 (Dynamic Creative) → stesso 322

Cancella prima la bozza precedente (campaign_id in DELETE_CAMPAIGN).
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
DELETE_CAMPAIGN = "120249093313100535"  # bozza precedente da rimuovere

IMG = ["918a547044ff14dedf432415aedba365",   # gialla
       "304444ec5a10f23afb670bd93cf41d72",   # secchio
       "c9ac5900c8cf6b3e05210feaa1224cf7"]   # numero

B1 = ("Fatturi più di 20k€/mese e la tua email si limita a qualche newsletter? "
      "Stai lasciando a terra 5-7k€ ogni mese.\n"
      "Non è traffico che ti manca: sono i flussi che non hai o che non funzionano — "
      "carrello abbandonato, post-acquisto, win-back.\n"
      "Quei soldi sono già nella tua lista. Vanno solo recuperati.\n"
      "Fai il test gratuito e scopri quanto stai perdendo 👇")
B2 = ("Il tuo eCommerce ha un problema che le ads non risolveranno mai.\n"
      "Ogni euro speso in Meta porta traffico dentro. Ma senza una macchina di retention, "
      "quei clienti escono dalla porta sul retro.\n"
      "Welcome flow assente. Carrello senza follow-up. Nessun post-acquisto. Nessun win-back.\n"
      "Scopri quanto stai perdendo ogni mese. Analisi gratuita, risultati in 48h 👇")
T1 = "Scopri il tuo potenziale email in 2 minuti"
T2 = "Il tuo eCom è un secchio bucato?"
DESC = "Analisi gratuita per chi fattura 20K+/mese"
N_ADSET = 3


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


def main():
    cfg = json.load(open(".tmp/322_source_config.json"))
    targeting = cfg["targeting"]
    state = {"adsets": []}

    if DELETE_CAMPAIGN:
        print("⌫ cancello bozza precedente…", delete(DELETE_CAMPAIGN))

    print("① Campagna CBO PAUSED (€31/gg a livello campagna)…")
    camp = post(f"{ACC}/campaigns", {
        "name": "AND1 · 322 Loss Aversion (CBO) — DRAFT",
        "objective": "OUTCOME_LEADS",
        "status": "PAUSED",
        "special_ad_categories": json.dumps([]),
        "daily_budget": 3100,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    })
    state["campaign_id"] = camp["id"]
    print("   ✅", camp["id"])

    afs = {
        "images": [{"hash": h} for h in IMG],
        "bodies": [{"text": B1}, {"text": B2}],
        "titles": [{"text": T1}, {"text": T2}],
        "descriptions": [{"text": DESC}],
        "ad_formats": ["SINGLE_IMAGE"],
        "call_to_action_types": [CTA],
        "link_urls": [{"website_url": LINK}],
    }

    for i in range(1, N_ADSET + 1):
        print(f"② Adset {i} (Dynamic Creative)…")
        adset = post(f"{ACC}/adsets", {
            "name": f"322 · Test {i} — IT eCom Owner Broad",
            "campaign_id": camp["id"],
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "promoted_object": json.dumps({"pixel_id": PIXEL_ID, "custom_event_type": "COMPLETE_REGISTRATION"}),
            "targeting": json.dumps(targeting),
            "is_dynamic_creative": "true",
            "status": "PAUSED",
        })
        print("   ✅ adset", adset["id"])
        cr = post(f"{ACC}/adcreatives", {
            "name": f"322 Test {i} — creative",
            "object_story_spec": json.dumps({"page_id": PAGE_ID}),
            "asset_feed_spec": json.dumps(afs),
        })
        ad = post(f"{ACC}/ads", {
            "name": f"322 · Test {i}",
            "adset_id": adset["id"],
            "creative": json.dumps({"creative_id": cr["id"]}),
            "status": "PAUSED",
        })
        print(f"   ✅ ad {ad['id']} / creative {cr['id']}")
        state["adsets"].append({"adset_id": adset["id"], "ad_id": ad["id"], "creative_id": cr["id"]})

    json.dump(state, open(".tmp/322_cbo_state.json", "w"), indent=2)
    print("\n✅ FATTO — tutto PAUSED.")
    print(f"Campaign: {state['campaign_id']}")
    print(f"Adsmanager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2390793521074673&selected_campaign_ids={state['campaign_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}")
        sys.exit(1)
