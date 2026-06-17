"""End-to-end test della pipeline verify-suppliers contro Gmail vero.

Requisiti:
    - Backend in ascolto su http://127.0.0.1:8001
        cd webapp/backend && source ../../.venv/bin/activate && uvicorn app.main:app --port 8001
    - Token Gmail (.tmp/token_*.json) presenti a root progetto
    - CSV reale in inbox/processed/
    - ANTHROPIC_API_KEY (opzionale; se assente il job finisce in pdf_only)

Uso:
    python webapp/backend/tests/test_verify_e2e.py
    python webapp/backend/tests/test_verify_e2e.py --base-url http://127.0.0.1:8001
    python webapp/backend/tests/test_verify_e2e.py --csv /path/to/file.csv

Exit code 0 = pass, 1 = fail.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[3]
INBOX = ROOT / "inbox" / "processed"

# Seed deterministico: fornitori presenti in SUPPLIERS (verify_suppliers_from_email.py)
# da iniettare come candidates quando classify fallisce (es. credit Anthropic esauriti).
# I nomi devono matchare _supplier_lookup() del service (key o substring del display_name).
SEED_CANDIDATES = [
    {"supplier_name": "Lovable Labs", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "SE", "supplier_vat_number": "",
     "source_transaction": {"description": "LOVABLE LABS SUBSCRIPTION", "amount": -25.0, "date": "2026-02-10", "currency": "EUR"}},
    {"supplier_name": "Apify Technologies", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "CZ", "supplier_vat_number": "",
     "source_transaction": {"description": "APIFY TECHNOLOGIES S.R.O", "amount": -49.0, "date": "2026-02-12", "currency": "EUR"}},
    {"supplier_name": "OpenAI", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "US", "supplier_vat_number": "",
     "source_transaction": {"description": "OPENAI CHATGPT SUBSCRIPTION", "amount": -22.0, "date": "2026-02-15", "currency": "EUR"}},
    {"supplier_name": "ElevenLabs", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "US", "supplier_vat_number": "",
     "source_transaction": {"description": "ELEVENLABS INC", "amount": -22.0, "date": "2026-02-18", "currency": "EUR"}},
    {"supplier_name": "Hostinger", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "LT", "supplier_vat_number": "",
     "source_transaction": {"description": "HOSTINGER INTERNATIONAL", "amount": -15.0, "date": "2026-02-20", "currency": "EUR"}},
    {"supplier_name": "Gamma Tech", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "US", "supplier_vat_number": "",
     "source_transaction": {"description": "GAMMA APP SUBSCRIPTION", "amount": -16.0, "date": "2026-02-22", "currency": "EUR"}},
]


def _seed_candidates_in_db(statement_id: str) -> int:
    """Scorciatoia E2E quando classify AI fallisce: iniettiamo direttamente i
    candidates nel DB della webapp via SQLAlchemy, poi build_preview() li
    raccoglie da lì. Usato SOLO se classify fallisce per credit_balance.
    """
    # Import lazy: richiede che PYTHONPATH includa webapp/backend per trovare `app.*`
    sys.path.insert(0, str(ROOT / "webapp" / "backend"))
    from app.services import workflow as workflow_svc  # type: ignore

    # Mark come "classificati"
    workflow_svc._statement_candidates[statement_id] = list(SEED_CANDIDATES)
    workflow_svc._statement_skipped[statement_id] = []
    workflow_svc._db_upsert_statement(
        statement_id,
        candidates=SEED_CANDIDATES,
        skipped_italian=[],
    )
    return len(SEED_CANDIDATES)


def _pick_csv(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).resolve()
        if not p.exists():
            raise SystemExit(f"CSV non trovato: {p}")
        return p
    if not INBOX.exists():
        raise SystemExit(f"cartella inbox/processed assente: {INBOX}")
    csvs = sorted(INBOX.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        raise SystemExit(f"nessun CSV in {INBOX}")
    return csvs[0]


def _poll_job(client: httpx.Client, job_id: str, timeout_s: float, label: str) -> dict:
    t0 = time.time()
    last_step = ""
    while time.time() - t0 < timeout_s:
        r = client.get(f"/api/jobs/{job_id}")
        r.raise_for_status()
        j = r.json()
        step = j.get("step_name", "")
        if step != last_step:
            print(f"  [{label}] {j['status']} {j.get('progress', 0)}% — {step}")
            last_step = step
        if j["status"] in ("done", "error"):
            return j
        time.sleep(2.0)
    raise TimeoutError(f"job {job_id} ({label}) timeout dopo {timeout_s}s")


def run(base_url: str, csv_path: Path, verify_timeout_s: float) -> int:
    print(f"== Verify E2E ==")
    print(f"base_url: {base_url}")
    print(f"csv: {csv_path}")
    print()

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        # Health
        h = client.get("/api/health")
        print(f"[health] {h.status_code} {h.json() if h.status_code == 200 else h.text}")
        if h.status_code != 200:
            print("! backend non risponde")
            return 1

        # 1. Upload
        with csv_path.open("rb") as f:
            r = client.post(
                "/api/statements/upload",
                files={"file": (csv_path.name, f, "text/csv")},
            )
        r.raise_for_status()
        statement_id = r.json()["statement_id"]
        print(f"[upload] statement_id={statement_id}")

        # 2. Parse
        r = client.post(f"/api/statements/{statement_id}/parse")
        r.raise_for_status()
        txs = r.json()
        print(f"[parse] {len(txs.get('transactions', []))} transazioni, outflows={txs.get('outflows_count')}")

        # 3. Classify (async) — se fallisce per credit Anthropic esauriti,
        # seediamo candidates direttamente in DB e proseguiamo (il verify
        # non dipende da Claude per la parte Gmail).
        r = client.post(f"/api/statements/{statement_id}/classify")
        r.raise_for_status()
        classify_job_id = r.json()["job_id"]
        print(f"[classify] job_id={classify_job_id}")
        jc = _poll_job(client, classify_job_id, timeout_s=180.0, label="classify")
        if jc["status"] != "done":
            err_txt = (jc.get("error") or "").lower()
            if "credit" in err_txt or "balance" in err_txt or "429" in err_txt or "rate" in err_txt:
                print(f"  (classify fallito per Anthropic credit/rate, seeding candidates in DB)")
                n = _seed_candidates_in_db(statement_id)
                print(f"  seeded {n} candidates via DB upsert")
            else:
                print(f"! classify failed: {jc.get('error')}")
                return 1
        else:
            af_count = jc.get("result", {}).get("autofatture_count", 0)
            print(f"[classify] done, autofatture={af_count}")

        # 4. Preview
        r = client.post(f"/api/statements/{statement_id}/preview")
        r.raise_for_status()
        prev = r.json()
        autofatture = prev.get("autofatture", [])
        print(f"[preview] {len(autofatture)} autofatture, skipped_italian={len(prev.get('skipped_italian', []))}")
        for af in autofatture[:10]:
            name = af.get("supplier_name")
            country = af.get("supplier_country_iso")
            is_eu = not af.get("is_extra_ue")
            print(f"    - {name:30} {country} {'UE' if is_eu else 'extra-UE'}")
        if len(autofatture) < 1:
            print("! preview vuoto, test non significativo")
            return 1
        if len(autofatture) < 5:
            print(f"  (warning) solo {len(autofatture)} autofatture, soglia consigliata 5")

        # 5. Verify suppliers
        r = client.post(f"/api/statements/{statement_id}/verify-suppliers")
        r.raise_for_status()
        verify_job_id = r.json()["job_id"]
        print(f"[verify] job_id={verify_job_id}, timeout={verify_timeout_s:.0f}s")
        jv = _poll_job(client, verify_job_id, timeout_s=verify_timeout_s, label="verify")
        if jv["status"] != "done":
            print(f"! verify failed: {jv.get('error')}")
            return 1

        # 6. Results
        r = client.get(f"/api/statements/{statement_id}/verify-suppliers/results")
        r.raise_for_status()
        results = r.json().get("results", [])
        print(f"\n== Verify results: {len(results)} fornitori ==")
        counts: dict[str, int] = {}
        for res in results:
            st = res.get("status", "unknown")
            counts[st] = counts.get(st, 0) + 1
        for st, c in sorted(counts.items()):
            print(f"  {st:20} {c}")
        print()
        for res in results:
            name = res.get("supplier_name", "")
            st = res.get("status", "")
            pdf_count = res.get("pdf_count", 0)
            err = res.get("error")
            warn = res.get("warning")
            extra = ""
            if err:
                extra = f"  ERROR: {err[:80]}"
            elif warn:
                extra = f"  warn: {warn[:80]}"
            print(f"  {name:30} {st:20} pdfs={pdf_count}{extra}")

        # Criterio: almeno un fornitore deve avere status tra {verified, pdf_only, bill_to_mismatch}
        ok_statuses = {"verified", "pdf_only", "bill_to_mismatch"}
        positives = sum(1 for r in results if r.get("status") in ok_statuses)
        print(f"\nPositives (verified|pdf_only|bill_to_mismatch): {positives}")
        if positives < 1:
            print("! nessun fornitore con risultato positivo — test fallito")
            return 1
        print("\n== E2E PASS ==")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8001")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--verify-timeout", type=float, default=600.0)
    args = ap.parse_args()
    csv_path = _pick_csv(args.csv)
    return run(args.base_url, csv_path, args.verify_timeout)


if __name__ == "__main__":
    sys.exit(main())
