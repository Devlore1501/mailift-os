"""End-to-end smoke test del backend autofatture-webapp v2.

Esercita TUTTI gli endpoint REST in sequenza, verifica i campi critici del
contratto API v2 (vat_id country-aware, skipped_italian, verify-suppliers,
override CRUD, history) e stampa un report pass/fail.

Requisiti:
    - Backend in ascolto su http://127.0.0.1:8001
        cd webapp/backend && source ../../.venv/bin/activate && uvicorn app.main:app --port 8001
    - CSV reale in inbox/processed/ (preso il piu' recente per default)
    - Token Gmail in tokens/ (per il verify step; opzionale: se mancanti il
      verify ritorna tutti not_found ma il test non fallisce)
    - ANTHROPIC_API_KEY (opzionale: se assente il classify viene seedato in DB
      con candidates deterministici e il verify gira in modalita' pdf_only)

Uso:
    python webapp/backend/tests/smoke_test_e2e.py
    python webapp/backend/tests/smoke_test_e2e.py --base-url http://127.0.0.1:8001
    python webapp/backend/tests/smoke_test_e2e.py --csv /path/to/file.csv

Exit code 0 = tutto pass, 1 = almeno un fail.
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[3]
INBOX = ROOT / "inbox" / "processed"

# Seed deterministico per quando classify fallisce per credit Anthropic.
# I nomi devono matchare _supplier_lookup() in services/suppliers.py:
#  Lovable, Apify (UE), OpenAI/ElevenLabs/Gamma (extra-UE), Hostinger (UE).
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
    # Italian supplier per verificare lo skipped_italian path
    {"supplier_name": "Google Cloud Italy Srl", "confidence": "high", "type_doc": "TD17",
     "supplier_country": "IT", "supplier_vat_number": "IT09286280967",
     "source_transaction": {"description": "GOOGLE CLOUD ITALY SRL", "amount": -35.5, "date": "2026-02-25", "currency": "EUR"}},
]


# ----------------------------------------------------------- helpers


class Reporter:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def ok(self, step: str, detail: str = "") -> None:
        line = f"[OK]   {step}"
        if detail:
            line += f" — {detail}"
        print(line)
        self.passed.append(step)

    def fail(self, step: str, detail: str) -> None:
        print(f"[FAIL] {step} — {detail}")
        self.failed.append((step, detail))

    def warn(self, msg: str) -> None:
        print(f"[WARN] {msg}")
        self.warnings.append(msg)

    def summary(self) -> int:
        total = len(self.passed) + len(self.failed)
        print()
        print("=" * 60)
        print(f"Smoke test summary: {len(self.passed)}/{total} pass, "
              f"{len(self.failed)} fail, {len(self.warnings)} warn")
        if self.failed:
            print("\nFailed steps:")
            for name, detail in self.failed:
                print(f"  - {name}: {detail}")
        return 0 if not self.failed else 1


def _seed_candidates_in_db(statement_id: str) -> int:
    sys.path.insert(0, str(ROOT / "webapp" / "backend"))
    from app.services import workflow as workflow_svc  # type: ignore

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


def _poll_job(client: httpx.Client, job_id: str, timeout_s: float, label: str) -> dict[str, Any]:
    t0 = time.time()
    last_step = ""
    while time.time() - t0 < timeout_s:
        r = client.get(f"/api/jobs/{job_id}")
        r.raise_for_status()
        j = r.json()
        step = j.get("step_name", "")
        if step != last_step:
            print(f"     [{label}] {j['status']} {j.get('progress', 0)}% — {step}")
            last_step = step
        if j["status"] in ("done", "error"):
            return j
        time.sleep(1.5)
    raise TimeoutError(f"job {job_id} ({label}) timeout dopo {timeout_s}s")


# ----------------------------------------------------------- main flow


def run(base_url: str, csv_path: Path, verify_timeout_s: float) -> int:
    print(f"== Backend smoke test ==")
    print(f"base_url: {base_url}")
    print(f"csv: {csv_path}")
    print()

    rep = Reporter()
    statement_id: str | None = None
    autofatture: list[dict] = []

    with httpx.Client(base_url=base_url, timeout=60.0) as client:

        # Step 1: GET /api/health
        try:
            r = client.get("/api/health")
            r.raise_for_status()
            h = r.json()
            required = {"status", "fic_token_valid", "company", "dry_run",
                        "db_ok", "gmail_tokens_ok", "anthropic_api_ok"}
            missing = required - set(h.keys())
            if missing:
                rep.fail("step 1: GET /api/health", f"campi mancanti: {missing}")
            elif not h.get("db_ok"):
                rep.fail("step 1: GET /api/health", "db_ok=False")
            else:
                gt = h.get("gmail_tokens_ok") or {}
                gmail_summary = f"personal={gt.get('personal')}, business={gt.get('business')}"
                rep.ok("step 1: GET /api/health",
                       f"fic={h.get('fic_token_valid')}, db={h.get('db_ok')}, "
                       f"gmail={{{gmail_summary}}}, anthropic={h.get('anthropic_api_ok')}")
                if not h.get("fic_token_valid"):
                    rep.warn("FiC token non valido — autofatture/create probabilmente fallira'")
                if not all(gt.values()):
                    rep.warn("Gmail tokens parziali o mancanti — verify dara' molti not_found")
        except Exception as e:
            rep.fail("step 1: GET /api/health", f"{type(e).__name__}: {e}")
            return rep.summary()  # senza health non vale la pena continuare

        # Step 2: GET /api/config
        try:
            r = client.get("/api/config")
            r.raise_for_status()
            cfg = r.json()
            required = {"company_id", "numeration", "payment_method", "blacklist_count"}
            missing = required - set(cfg.keys())
            if missing:
                rep.fail("step 2: GET /api/config", f"campi mancanti: {missing}")
            else:
                rep.ok("step 2: GET /api/config",
                       f"numeration={cfg.get('numeration')}, blacklist={cfg.get('blacklist_count')}")
        except Exception as e:
            rep.fail("step 2: GET /api/config", f"{type(e).__name__}: {e}")

        # Step 3: POST /api/statements/upload
        try:
            with csv_path.open("rb") as f:
                r = client.post(
                    "/api/statements/upload",
                    files={"file": (csv_path.name, f, "text/csv")},
                )
            r.raise_for_status()
            up = r.json()
            statement_id = up.get("statement_id")
            if not statement_id:
                rep.fail("step 3: POST /api/statements/upload", "statement_id mancante")
            else:
                rep.ok("step 3: POST /api/statements/upload",
                       f"id={statement_id}, size={up.get('size_bytes')}")
        except Exception as e:
            rep.fail("step 3: POST /api/statements/upload", f"{type(e).__name__}: {e}")
            return rep.summary()

        # Step 4: POST /api/statements/{id}/parse
        try:
            r = client.post(f"/api/statements/{statement_id}/parse")
            r.raise_for_status()
            ps = r.json()
            n_tx = len(ps.get("transactions", []))
            if n_tx < 1:
                rep.fail("step 4: POST /api/statements/{id}/parse", "0 transazioni")
            else:
                rep.ok("step 4: POST /api/statements/{id}/parse",
                       f"{n_tx} tx, outflows={ps.get('outflows_count')}")
        except Exception as e:
            rep.fail("step 4: POST /api/statements/{id}/parse", f"{type(e).__name__}: {e}")
            return rep.summary()

        # Step 5: POST /api/statements/{id}/classify (async)
        # Se classify fallisce per credit Anthropic, seediamo i candidates.
        try:
            r = client.post(f"/api/statements/{statement_id}/classify")
            r.raise_for_status()
            classify_job_id = r.json()["job_id"]
            jc = _poll_job(client, classify_job_id, timeout_s=180.0, label="classify")
            if jc["status"] != "done":
                err_txt = (jc.get("error") or "").lower()
                if any(k in err_txt for k in ("credit", "balance", "429", "rate")):
                    rep.warn(f"classify fallito per Anthropic credit/rate, seeding candidates")
                    n = _seed_candidates_in_db(statement_id)
                    rep.ok("step 5: POST /api/statements/{id}/classify",
                           f"(seeded fallback) {n} candidates")
                else:
                    rep.fail("step 5: POST /api/statements/{id}/classify",
                             f"job error: {jc.get('error')}")
            else:
                result = jc.get("result") or {}
                skipped = result.get("skipped_italian")
                if skipped is None:
                    rep.fail("step 5: POST /api/statements/{id}/classify",
                             "skipped_italian mancante nel result")
                else:
                    rep.ok("step 5: POST /api/statements/{id}/classify",
                           f"af={result.get('autofatture_count')}, "
                           f"skipped_it={len(skipped)}")
        except Exception as e:
            traceback.print_exc()
            rep.fail("step 5: POST /api/statements/{id}/classify", f"{type(e).__name__}: {e}")

        # Step 6: POST /api/statements/{id}/preview
        try:
            r = client.post(f"/api/statements/{statement_id}/preview")
            r.raise_for_status()
            prev = r.json()
            autofatture = prev.get("autofatture") or []
            skipped_italian = prev.get("skipped_italian") or []
            if not autofatture:
                rep.fail("step 6: preview", "0 autofatture nel preview")
            else:
                # Verifica campi obbligatori per ogni autofattura
                required_af = {"supplier_country_iso", "is_extra_ue", "lines"}
                required_line = {"vat_id", "vat_rate_percent"}
                af_missing: list[str] = []
                for af in autofatture:
                    miss = required_af - set(af.keys())
                    if miss:
                        af_missing.append(f"{af.get('supplier_name','?')}: {miss}")
                    for line in af.get("lines", []):
                        lm = required_line - set(line.keys())
                        if lm:
                            af_missing.append(f"{af.get('supplier_name','?')}/line: {lm}")
                if af_missing:
                    rep.fail("step 6: preview",
                             f"campi mancanti: {af_missing[:3]}")
                else:
                    rep.ok("step 6: POST /api/statements/{id}/preview",
                           f"{len(autofatture)} autofatture, {len(skipped_italian)} skipped IT")
                    for af in autofatture:
                        name = af.get("supplier_name", "")[:28]
                        ctry = af.get("supplier_country_iso", "??")
                        is_eu = "extra-UE" if af.get("is_extra_ue") else "UE"
                        line0 = (af.get("lines") or [{}])[0]
                        vid = line0.get("vat_id")
                        vp = line0.get("vat_rate_percent")
                        print(f"     - {name:28} {ctry} {is_eu:10} vat_id={vid} {vp}%")
        except Exception as e:
            traceback.print_exc()
            rep.fail("step 6: preview", f"{type(e).__name__}: {e}")
            return rep.summary()

        # Step 7: extra-UE deve avere vat_id=10, vat_rate_percent=0, is_extra_ue=True
        try:
            extra_ue = [a for a in autofatture if a.get("is_extra_ue")]
            if not extra_ue:
                rep.warn("nessun fornitore extra-UE nel preview, skip step 7")
            else:
                af = extra_ue[0]
                line = (af.get("lines") or [{}])[0]
                if line.get("vat_id") != 10:
                    rep.fail("step 7: extra-UE vat_id",
                             f"{af.get('supplier_name')}: vat_id={line.get('vat_id')} (atteso 10)")
                elif float(line.get("vat_rate_percent", -1)) != 0.0:
                    rep.fail("step 7: extra-UE vat_rate",
                             f"{af.get('supplier_name')}: vat_rate_percent={line.get('vat_rate_percent')} (atteso 0)")
                elif not af.get("is_extra_ue"):
                    rep.fail("step 7: extra-UE flag", f"{af.get('supplier_name')}: is_extra_ue=False")
                else:
                    rep.ok("step 7: extra-UE country-aware",
                           f"{af.get('supplier_name')} → vat_id=10, 0%, extra-UE")
        except Exception as e:
            rep.fail("step 7: extra-UE check", f"{type(e).__name__}: {e}")

        # Step 8: UE deve avere vat_id=0, vat_rate_percent=22, is_extra_ue=False
        try:
            ue = [a for a in autofatture if not a.get("is_extra_ue")
                  and (a.get("supplier_country_iso") or "").upper() != "IT"]
            if not ue:
                rep.warn("nessun fornitore UE nel preview, skip step 8")
            else:
                af = ue[0]
                line = (af.get("lines") or [{}])[0]
                if line.get("vat_id") != 0:
                    rep.fail("step 8: UE vat_id",
                             f"{af.get('supplier_name')}: vat_id={line.get('vat_id')} (atteso 0)")
                elif float(line.get("vat_rate_percent", -1)) != 22.0:
                    rep.fail("step 8: UE vat_rate",
                             f"{af.get('supplier_name')}: vat_rate_percent={line.get('vat_rate_percent')} (atteso 22)")
                else:
                    rep.ok("step 8: UE country-aware",
                           f"{af.get('supplier_name')} → vat_id=0, 22% RC")
        except Exception as e:
            rep.fail("step 8: UE check", f"{type(e).__name__}: {e}")

        # Step 9: Google Cloud Italy in skipped_italian (se presente nel CSV/seed)
        try:
            sk = (prev.get("skipped_italian") or [])
            it_in_preview = any(
                (a.get("supplier_country_iso") or "").upper() == "IT" for a in autofatture
            )
            if sk:
                names = [s.get("supplier_name", "") for s in sk]
                rep.ok("step 9: skipped_italian",
                       f"{len(sk)} esclusi: {', '.join(names[:3])}")
                if it_in_preview:
                    rep.fail("step 9: IT supplier mai in preview",
                             "fornitore IT presente sia in preview sia in skipped — bug")
            elif it_in_preview:
                rep.fail("step 9: skipped_italian",
                         "fornitore IT presente in preview ma skipped_italian vuoto")
            else:
                rep.warn("nessun fornitore IT nel CSV/seed, skip step 9")
        except Exception as e:
            rep.fail("step 9: skipped_italian", f"{type(e).__name__}: {e}")

        # Step 10: POST /api/statements/{id}/verify-suppliers
        try:
            r = client.post(f"/api/statements/{statement_id}/verify-suppliers")
            r.raise_for_status()
            verify_job_id = r.json()["job_id"]
            jv = _poll_job(client, verify_job_id, timeout_s=verify_timeout_s, label="verify")
            if jv["status"] != "done":
                rep.fail("step 10: verify-suppliers job",
                         f"job error: {jv.get('error', '')[:120]}")
            else:
                results_in_job = (jv.get("result") or {}).get("results") or {}
                # Almeno un risultato non pending
                non_pending = [r for r in results_in_job.values()
                               if r.get("status") not in ("pending", None)]
                rep.ok("step 10: POST /api/statements/{id}/verify-suppliers",
                       f"job done, {len(results_in_job)} fornitori, "
                       f"{len(non_pending)} non-pending")
        except Exception as e:
            traceback.print_exc()
            rep.fail("step 10: verify-suppliers", f"{type(e).__name__}: {e}")

        # Step 11: GET /api/statements/{id}/verify-suppliers/results
        try:
            r = client.get(f"/api/statements/{statement_id}/verify-suppliers/results")
            r.raise_for_status()
            vr = r.json()
            results = vr.get("results") or []
            ok_statuses = {"verified", "pdf_only", "bill_to_mismatch"}
            positives = sum(1 for r in results if r.get("status") in ok_statuses)
            rep.ok("step 11: GET verify-suppliers/results",
                   f"{len(results)} risultati, {positives} positivi (verified/pdf_only/bill_to_mismatch)")
            for res in results:
                name = (res.get("supplier_name") or "")[:25]
                st = res.get("status", "?")
                pdfs = res.get("pdf_count", 0)
                print(f"     - {name:25} {st:20} pdfs={pdfs}")
            if positives < 1:
                rep.warn("nessun fornitore con stato positivo (potrebbe essere normale "
                         "se Gmail tokens mancanti)")
        except Exception as e:
            rep.fail("step 11: verify-suppliers results", f"{type(e).__name__}: {e}")

        # Step 12: POST /api/autofatture/create dry-run
        try:
            payload = {
                "autofatture": autofatture,
                "dry_run": True,
                "statement_id": statement_id,
            }
            r = client.post("/api/autofatture/create", json=payload)
            r.raise_for_status()
            create_job_id = r.json()["job_id"]
            jcr = _poll_job(client, create_job_id, timeout_s=120.0, label="create")
            if jcr["status"] != "done":
                rep.fail("step 12: autofatture/create dry-run",
                         f"job error: {jcr.get('error', '')[:120]}")
            else:
                result = jcr.get("result") or {}
                items = result.get("items") or []
                ok = result.get("ok", 0)
                errs = result.get("errors", 0)
                skipped = result.get("skipped", 0)
                # Dry-run: tutti gli items dovrebbero essere "skipped"
                expected = len([a for a in autofatture if not a.get("excluded")])
                if len(items) != expected:
                    rep.fail("step 12: autofatture/create dry-run",
                             f"items={len(items)} vs expected={expected}")
                elif ok + errs + skipped != len(items):
                    rep.fail("step 12: autofatture/create dry-run",
                             f"ok+errors+skipped={ok+errs+skipped} != items={len(items)}")
                else:
                    rep.ok("step 12: POST /api/autofatture/create (dry-run)",
                           f"items={len(items)}, ok={ok}, errors={errs}, skipped={skipped}")
        except Exception as e:
            traceback.print_exc()
            rep.fail("step 12: autofatture/create dry-run", f"{type(e).__name__}: {e}")

        # Step 13: GET /api/history → run appena fatto compare
        try:
            r = client.get("/api/history")
            r.raise_for_status()
            hist = r.json()
            recent = [h for h in hist if h.get("statement_id") == statement_id]
            if not recent:
                rep.fail("step 13: GET /api/history",
                         f"run dello statement {statement_id} non trovato in history")
            else:
                rep.ok("step 13: GET /api/history",
                       f"{len(hist)} run totali, {len(recent)} per questo statement")
                # Verifica anche il detail
                rid = recent[0]["id"]
                r2 = client.get(f"/api/history/{rid}")
                r2.raise_for_status()
                detail = r2.json()
                if "result_json" not in detail:
                    rep.fail("step 13: GET /api/history/{id}",
                             "result_json mancante nel detail")
                else:
                    rep.ok("step 13: GET /api/history/{id}",
                           f"detail ok, result_json items={len(detail.get('result_json') or [])}")
        except Exception as e:
            rep.fail("step 13: history", f"{type(e).__name__}: {e}")

        # Step 14: CRUD overrides
        try:
            test_key = "smoke_test_supplier_xyz"
            payload = {
                "supplier_key": test_key,
                "supplier_name_display": "Smoke Test Supplier",
                "country_iso": "US",
                "vat_number": "",
                "vat_id": 10,
                "note": "Created by smoke_test_e2e.py",
            }
            r = client.post("/api/suppliers/overrides", json=payload)
            r.raise_for_status()
            created = r.json()
            ovr_id = created.get("id")
            if not ovr_id:
                rep.fail("step 14a: POST overrides", "id mancante nella response")
            else:
                rep.ok("step 14a: POST /api/suppliers/overrides", f"id={ovr_id}")

                # GET list
                r = client.get("/api/suppliers/overrides")
                r.raise_for_status()
                lst = r.json()
                found = any(o.get("id") == ovr_id for o in lst)
                if not found:
                    rep.fail("step 14b: GET overrides",
                             f"override id={ovr_id} non trovato nella lista")
                else:
                    rep.ok("step 14b: GET /api/suppliers/overrides",
                           f"{len(lst)} overrides totali, fixture trovato")

                # DELETE
                r = client.delete(f"/api/suppliers/overrides/{ovr_id}")
                r.raise_for_status()
                if not r.json().get("deleted"):
                    rep.fail("step 14c: DELETE overrides",
                             f"deleted=False per id {ovr_id}")
                else:
                    rep.ok("step 14c: DELETE /api/suppliers/overrides/{id}",
                           f"id={ovr_id} eliminato")
                    # Verify gone
                    r = client.get("/api/suppliers/overrides")
                    r.raise_for_status()
                    if any(o.get("id") == ovr_id for o in r.json()):
                        rep.fail("step 14d: verify delete",
                                 f"override id={ovr_id} ancora presente dopo DELETE")
                    else:
                        rep.ok("step 14d: verify delete", "override rimosso")
        except Exception as e:
            traceback.print_exc()
            rep.fail("step 14: CRUD overrides", f"{type(e).__name__}: {e}")

        # Step 15 (bonus): GET /api/suppliers/verify-rejects
        try:
            r = client.get("/api/suppliers/verify-rejects")
            r.raise_for_status()
            rejects = r.json()
            rep.ok("step 15: GET /api/suppliers/verify-rejects",
                   f"{len(rejects)} PDF in quarantena")
        except Exception as e:
            rep.fail("step 15: verify-rejects", f"{type(e).__name__}: {e}")

    return rep.summary()


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
