#!/usr/bin/env python3
"""Watcher: testa ogni 5 min se Meta ha sbloccato la creazione creative (subcode 1487390).
Appena sbloccato, esegue il reload completo (swap_images_and_live.main) e scrive il flag.
Cap: ~2 ore.
"""
import sys, json, time
sys.path.insert(0, "tools")
from fb_ads_client import ACCESS_TOKEN, GRAPH_BASE
import requests
ACC = "act_2390793521074673"

def probe():
    spec = {"page_id": "101236142286783", "link_data": {
        "image_hash": "9cc7ae77042f77df955a12e4a2f3498f",
        "link": "https://mailift.com/optin-calcolatore-page", "message": "probe", "name": "probe",
        "call_to_action": {"type": "SEE_DETAILS", "value": {"link": "https://mailift.com/optin-calcolatore-page"}}}}
    try:
        r = requests.post(f"{GRAPH_BASE}/{ACC}/adcreatives",
                          data={"access_token": ACCESS_TOKEN, "name": "probe_unblock", "object_story_spec": json.dumps(spec)}, timeout=60)
    except Exception as e:
        print(f"    (probe network error: {type(e).__name__}) → tratto come bloccato", flush=True)
        return False
    if r.status_code == 200:
        cid = r.json().get("id")
        if cid:
            try: requests.delete(f"{GRAPH_BASE}/{cid}", params={"access_token": ACCESS_TOKEN}, timeout=30)
            except Exception: pass
        return True
    return False

def main():
    for i in range(24):  # 24 * 5min = 2h
        if probe():
            print(f"[{i}] Meta SBLOCCATO → eseguo reload", flush=True)
            import swap_images_and_live as sw
            sw.main()
            open(".tmp/watch_DONE.txt", "w").write("reload done")
            return
        print(f"[{i}] ancora bloccato (1487390), riprovo tra 5 min", flush=True)
        time.sleep(300)
    open(".tmp/watch_TIMEOUT.txt", "w").write("still blocked after 2h")
    print("TIMEOUT: ancora bloccato dopo 2h", flush=True)

if __name__ == "__main__":
    main()
