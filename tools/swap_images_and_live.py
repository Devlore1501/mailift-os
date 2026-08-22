#!/usr/bin/env python3
"""Sostituisce le immagini (versioni senza badge 15K) nelle ad e mette LIVE il test.
Retry a backoff contro il throttle Meta (subcode 1487390 / 500 transient).

- Bank campaign (322 futuri): swap immagini 02-13, 15-20
- Main test campaign: swap 01 (Secchio) e 14 (Numero); poi ATTIVA campagna+adset+ad.
Immagini nuove: .tmp/manus_new/NN_*.png
"""
from __future__ import annotations
import sys, json, time, glob
sys.path.insert(0, "tools")
from fb_ads_client import ACCESS_TOKEN, GRAPH_BASE
import requests

ACC = "act_2390793521074673"
PAGE = "101236142286783"
DOF = json.dumps({"creative_features_spec": {"standard_enhancements": {"enroll_status": "OPT_OUT"}}})
MAIN_CAMP = "120249093656760535"

def _post(path, data=None, files=None):
    d = {"access_token": ACCESS_TOKEN}
    if data: d.update(data)
    try:
        r = requests.post(f"{GRAPH_BASE}/{path}", data=d, files=files, timeout=180)
    except Exception as e:
        return 599, {"error": {"is_transient": True, "message": f"net:{type(e).__name__}"}}
    try: j = r.json()
    except Exception: j = {"raw": r.text}
    return r.status_code, j

def _get(path, **p):
    p["access_token"] = ACCESS_TOKEN
    for _ in range(6):
        try:
            r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
            return r.status_code, r.json()
        except Exception:
            time.sleep(10)
    r = requests.get(f"{GRAPH_BASE}/{path}", params=p, timeout=60)
    return r.status_code, r.json()

def retry_post(path, data=None, files=None, tries=15, label=""):
    delay = 20
    for i in range(tries):
        sc, j = _post(path, data, files)
        if sc == 200:
            return j
        err = j.get("error", {})
        sub = err.get("error_subcode"); code = err.get("code")
        transient = err.get("is_transient") or sub in (1487390, 1487197) or code == 2 or sc >= 500
        print(f"    [{label}] try{i+1} {sc} sub={sub} → {'retry' if transient else 'FATAL'} {str(err.get('error_user_title') or err.get('message'))[:60]}", flush=True)
        if not transient:
            raise RuntimeError(f"{label}: {json.dumps(err)[:200]}")
        time.sleep(delay); delay = min(delay + 15, 90)
    raise RuntimeError(f"{label}: esaurito i retry (throttle Meta ancora attivo)")

def upload(nn):
    cands = sorted(glob.glob(f".tmp/manus_new/{nn}_*.jpg") + glob.glob(f".tmp/manus_new/{nn}_*.png"))
    path = cands[0]
    ext = ".jpg" if path.endswith(".jpg") else ".png"
    ctype = "image/jpeg" if ext == ".jpg" else "image/png"
    with open(path, "rb") as f:
        j = retry_post(f"{ACC}/adimages", files={"filename": (f"{nn}{ext}", f, ctype)}, label=f"upload {nn}")
    return list(j["images"].values())[0]["hash"]

def swap_ad(ad_id, new_hash, nn):
    sc, ad = _get(ad_id, fields="creative{object_story_spec}")
    oss = ad["creative"]["object_story_spec"]
    ld = oss.get("link_data") or {}
    ld["image_hash"] = new_hash
    oss["link_data"] = ld
    cr = retry_post(f"{ACC}/adcreatives", data={"name": f"{nn} no15k", "object_story_spec": json.dumps(oss)}, label=f"creative {nn}")
    retry_post(ad_id, data={"creative": json.dumps({"creative_id": cr["id"]})}, label=f"ad {nn}")
    return cr["id"]

def main():
    # mapping NN -> [ad_id]
    updates = {}
    bank = json.load(open(".tmp/322_bank_state.json"))
    for a in bank["adsets"]:
        for ad in a["ads"]:
            nn = ad["name"][:2]
            updates.setdefault(nn, []).append(ad["ad_id"])
    # main test immagini: [gialla, secchio, numero]
    main = json.load(open(".tmp/322_cbo3_state.json"))
    g, s, n = main["adsets"]["immagini"]["ads"]
    updates.setdefault("01", []).append(s)   # secchio
    updates.setdefault("14", []).append(n)   # numero

    import os
    done = {}
    if os.path.exists(".tmp/swap_state.json"):
        done = json.load(open(".tmp/swap_state.json"))
        print(f"resume: {len(done)} ad già fatte, le salto", flush=True)
    for nn in sorted(updates):
        pending = [a for a in updates[nn] if a not in done]
        if not pending:
            continue
        print(f"→ {nn} ({len(pending)} ad)", flush=True)
        h = upload(nn)
        for ad_id in pending:
            cid = swap_ad(ad_id, h, nn)
            done[ad_id] = {"nn": nn, "hash": h, "creative_id": cid}
            print(f"    ✅ ad {ad_id} → {h}", flush=True)
            time.sleep(2)
        json.dump(done, open(".tmp/swap_state.json", "w"), indent=2)

    print(f"\n✅ SWAP completato: {len(done)} ad aggiornate (tutto ancora in PAUSA).", flush=True)
    open(".tmp/swap_DONE.txt", "w").write("done")
    # go-live gestito a parte dopo conferma (rischio doppia spesa con campagna già live)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ INTERROTTO: {e}", flush=True)
        open(".tmp/swap_live_ERROR.txt", "w").write(str(e))
        sys.exit(1)
