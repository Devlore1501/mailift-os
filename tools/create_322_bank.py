#!/usr/bin/env python3
"""Banca 322 per test futuri — bozza PAUSED.
Nuova campagna CBO con 6 adset TEMATICI, ognuno = 3 ad singole separate
(no DCO), riusando le creative ESISTENTI (image+copy+headline già pronti).

Escluse 01 Secchio e 14 Numero (già nel test attivo).
"""
from __future__ import annotations
import sys, json
sys.path.insert(0, "tools")
from fb_ads_client import ACCESS_TOKEN, GRAPH_BASE
import requests

ACC = "act_2390793521074673"
PIXEL_ID = "1142953766808623"

# 6 adset tematici → (nome adset, [(nome ad, creative_id esistente), ...])
GROUPS = [
    ("322 · Dipendenza da Meta", [
        ("07 Meta In Pugno", "1712271089917101"),
        ("03 Matematica Brutale", "1034142702343130"),
        ("04 Vincitore", "1785474816206510"),
    ]),
    ("322 · Loss Aversion / Loop", [
        ("02 Tassa Silenziosa", "1083553437671479"),
        ("12 Loop Infinito", "1658931158509114"),
        ("13 Prima Dopo", "2024121441828295"),
    ]),
    ("322 · LTV / Metriche", [
        ("06 Esperto Dilettante", "1014606898020001"),
        ("18 LTV Pozzo", "1735890534086447"),
        ("08 Meta Vs Email", "1441413187815949"),
    ]),
    ("322 · Piattaforme / Attenzione", [
        ("09 Virale Non Business", "4448258505412480"),
        ("10 Lavorando Per TikTok", "1324489916432486"),
        ("05 Brand Vs Shop", "1309621094265290"),
    ]),
    ("322 · Recupero / Sconti", [
        ("16 Carrelli Fantasma", "1510068363678954"),
        ("15 Sconti Profitto", "1303379211577063"),
        ("17 Welcome Flow", "1344823657259596"),
    ]),
    ("322 · Founder / Setup", [
        ("11 Fondatore Solitario", "1052897233861045"),
        ("19 Non Ho Tempo", "27820611540962999"),
        ("20 Klaviyo Non Basta", "2253236758761638"),
    ]),
]


def post(path, data):
    data = {**data, "access_token": ACCESS_TOKEN}
    r = requests.post(f"{GRAPH_BASE}/{path}", data=data, timeout=60)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {json.dumps(j.get('error', j), ensure_ascii=False)[:300]}")
    return j


def main():
    cfg = json.load(open(".tmp/322_source_config.json"))
    tg = cfg["targeting"]
    state = {"adsets": []}

    print("① Campagna CBO Banca PAUSED €31/gg…")
    camp = post(f"{ACC}/campaigns", {
        "name": "AND1 · 322 · Banca Test Futuri — DRAFT", "objective": "OUTCOME_LEADS",
        "status": "PAUSED", "special_ad_categories": json.dumps([]),
        "daily_budget": 3100, "bid_strategy": "LOWEST_COST_WITHOUT_CAP"})
    state["campaign_id"] = camp["id"]
    print("   ✅", camp["id"])

    for adset_name, ads in GROUPS:
        print(f"② {adset_name}…")
        adset = post(f"{ACC}/adsets", {
            "name": adset_name, "campaign_id": camp["id"],
            "billing_event": "IMPRESSIONS", "optimization_goal": "OFFSITE_CONVERSIONS",
            "promoted_object": json.dumps({"pixel_id": PIXEL_ID, "custom_event_type": "COMPLETE_REGISTRATION"}),
            "targeting": json.dumps(tg), "status": "PAUSED"})
        print("   ✅ adset", adset["id"])
        made = []
        for ad_name, creative_id in ads:
            ad = post(f"{ACC}/ads", {
                "name": ad_name, "adset_id": adset["id"],
                "creative": json.dumps({"creative_id": creative_id}), "status": "PAUSED"})
            print(f"      ✅ {ad_name}: ad {ad['id']}")
            made.append({"name": ad_name, "ad_id": ad["id"], "creative_id": creative_id})
        state["adsets"].append({"name": adset_name, "adset_id": adset["id"], "ads": made})

    json.dump(state, open(".tmp/322_bank_state.json", "w"), indent=2)
    print("\n✅ FATTO — banca 322 tutta PAUSED.")
    print(f"Campaign: {state['campaign_id']}")
    print(f"Adsmanager: https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=2390793521074673&selected_campaign_ids={state['campaign_id']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}")
        try:
            json.dump(locals().get("state", {}), open(".tmp/322_bank_state.json", "w"), indent=2)
        except Exception:
            pass
        sys.exit(1)
