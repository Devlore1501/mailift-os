"""E2E backend su estratto reale, senza Anthropic e senza scritture FiC."""
import glob, json, os, sys, time
os.environ.update(WEBAPP_DATA_DIR=sys.argv[1], WEBAPP_PASSWORD="test-pw", WEBAPP_SECRET="x" * 32)
sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from app.main import app
from app.services import workflow
import autofatture_prep as prep

ROOT = "/Users/lorenzobaretta/workflow ai"
with TestClient(app) as c:
    assert c.get("/api/statements/x/preview").status_code == 401, "API deve essere protetta"
    assert c.post("/api/auth/login", json={"password": "no"}).status_code == 401
    assert c.post("/api/auth/login", json={"password": "test-pw"}).status_code == 200
    assert c.get("/api/auth/me").json()["authenticated"]
    pdf = f"{ROOT}/inbox/processed/revolut_2026-08_2026-11.pdf"
    r = c.post("/api/statements/upload", files={"file": ("estratto.pdf", open(pdf, "rb"), "application/pdf")})
    sid = r.json()["statement_id"]
    p = c.post(f"/api/statements/{sid}/parse").json()
    print("parse:", len(p["transactions"]), "tx, catena saldi", p["balance_check"]["checked"], "ok,", len(p["balance_check"]["errors"]), "errori")
    # Classificazione: candidati reali della sessione scorsa al posto della chiamata Anthropic
    txs = workflow._load_transactions(sid)
    pr = prep.prepare(txs)
    excluded_keys = {(e["date"], round(abs(e["amount"]), 2)) for e in pr["excluded"]}
    cands = []
    for f in sorted(glob.glob(f"{ROOT}/.tmp/cand_2026-*.json")):
        for cd in json.load(open(f)):
            s = cd["source_transaction"]
            if (s["date"], round(abs(s["amount"]), 2)) not in excluded_keys:
                cands.append(cd)
    workflow._db_upsert_statement(sid, excluded=pr["excluded"], orphan_refunds=pr["orphan_refunds"], candidates=cands, skipped_italian=[])
    workflow._statement_candidates[sid] = cands
    workflow._statement_skipped[sid] = []
    t0 = time.time()
    pv = c.post(f"/api/statements/{sid}/preview").json()
    af = pv["autofatture"]
    net = sum(l["amount_net"] for a in af for l in a["lines"])
    print(f"preview: {len(af)} autofatture, netto {net:.2f}, {time.time()-t0:.1f}s")
    print("  duplicate_check_ok:", pv["duplicate_check_ok"], "| segnalate:", sum(1 for a in af if a["duplicate"]),
          "| certe:", sum(1 for a in af if a["duplicate"] and a["duplicate"]["level"] == "duplicate"))
    print("  escluse:", {x["reason"]: sum(1 for y in pv["excluded"] if y["reason"] == x["reason"]) for x in pv["excluded"]})
    print("  rimborsi orfani:", [(o["date"], o["amount"]) for o in pv["orphan_refunds"]])
    months = {}
    for a in af:
        m = (a["ref_invoice_date"] or "")[:7]; months[m] = months.get(m, 0) + 1
    print("  per mese:", months)
    meta = [a for a in af if "meta" in a["supplier_name"].lower()]
    print("  Meta:", [(a["ref_invoice_date"], a["lines"][0]["amount_net"], a["lines"][0]["vat_rate_percent"]) for a in meta])
    # create dry-run
    j = c.post("/api/autofatture/create", json={"autofatture": af[:3], "dry_run": True, "statement_id": sid}).json()
    for _ in range(50):
        st = c.get(f"/api/jobs/{j['job_id']}").json()
        if st["status"] in {"done", "error"}: break
        time.sleep(0.2)
    print("create dry-run:", st["status"], st["result"]["skipped"] if st.get("result") else st.get("error"))
    # SDI: lista read-only + rifiuto invio senza conferma
    d = c.get("/api/sdi/documents", params={"date": "2026-11-19"}).json()
    print("sdi documents 19/11:", len(d["documents"]), {x["ei_status"] for x in d["documents"]})
    r = c.post("/api/sdi/send", json={"doc_ids": [d["documents"][0]["id"]], "confirm": "si"})
    print("sdi send senza parola di conferma ->", r.status_code)
    print("healthz", c.get("/api/healthz").json(), "| health fic:", c.get("/api/health").json()["fic_token_valid"])
