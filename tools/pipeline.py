#!/usr/bin/env python3
"""
Orchestratore della pipeline creative.

Stage in sequenza, ognuno registrato nella tabella runs con esito e durata:

  import   Meta → DB (metriche giornaliere + adset + evento di ottimizzazione)
  assets   scarica gli asset finché gli URL fbcdn sono vivi
  classify Claude classifica angolo / awareness / hook
  analyze  quali angoli hanno dati sufficienti per una decisione
  generate Manus produce varianti per un angolo eleggibile (richiede --angle)

`run all` esegue import → assets → classify → analyze. La generazione resta
fuori dal giro automatico di proposito: costa crediti e ha senso solo quando
analyze dice che c'è qualcosa da variare.

CLI:
  python tools/pipeline.py run all
  python tools/pipeline.py run import
  python tools/pipeline.py run generate --angle secchio-bucato
  python tools/pipeline.py status
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime

from creative_db import connect, min_leads
from pipeline_config import (ensure, finish_run, get, recent_runs, reconcile_runs,
                             start_run)

STAGES = ("import", "assets", "classify", "analyze", "generate", "render")
# generate e render restano fuori: consumano crediti Manus e hanno senso solo
# quando analyze dice che c'è qualcosa da variare.
AUTO_STAGES = ("import", "assets", "classify", "analyze")


# ── stage ─────────────────────────────────────────────────────────────────────

def stage_import(conn, **kw) -> str:
    from creative_db import RateLimited, import_history
    days = get("import_days", conn)
    accounts = get("accounts", conn)
    done = []
    for acct in accounts:
        try:
            import_history(acct, days)
            done.append(acct)
        except RateLimited as e:
            # Throttling non e' un fallimento dei dati gia' importati.
            raise RuntimeError(f"Meta rate limit dopo {len(done)}/{len(accounts)} account: {e}")
    n = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    return f"{len(done)} account, {n} creative in DB, {days} giorni"


def stage_assets(conn, **kw) -> str:
    from creative_assets import download
    rc = download(force=False)
    got = conn.execute("""SELECT COUNT(*) c FROM creatives
                          WHERE asset_path IS NOT NULL AND asset_path != ''""").fetchone()["c"]
    tot = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    if rc != 0:
        raise RuntimeError(f"download con errori — {got}/{tot} asset presenti")
    return f"{got}/{tot} asset in locale"


def stage_classify(conn, **kw) -> str:
    from creative_classifier import classify
    done, reused, failed = classify(limit=None, force=False, quiet=True)
    tot = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    cls = conn.execute("""SELECT COUNT(*) c FROM creatives
                          WHERE angle IS NOT NULL AND angle != ''""").fetchone()["c"]
    if failed:
        raise RuntimeError(f"{failed} classificazioni fallite — {cls}/{tot} classificati")
    return f"{done} nuovi, {reused} da cache — {cls}/{tot} classificati"


def stage_analyze(conn, **kw) -> str:
    """Non chiama nulla: legge il DB e dice se c'è qualcosa su cui decidere."""
    from manus_bridge import angle_stats
    stats = angle_stats(conn)
    if not stats:
        return "nessun angolo in una classe con lead veri — niente da analizzare"
    ok = [s for s in stats if s["enough"]]
    T = min_leads()
    parts = [f"{len(stats)} angoli, {len(ok)} sopra la soglia di {T} lead"]
    if ok:
        parts.append("generabili: " + ", ".join(f"{s['angle']} ({s['leads']} lead)" for s in ok))
    else:
        best = max(stats, key=lambda x: x["leads"])
        parts.append(f"il migliore è '{best['angle']}' con {best['leads']} lead: "
                     f"serve più volume, non più varianti")
    return " · ".join(parts)


def stage_generate(conn, angle: str | None = None, **kw) -> str:
    from manus_bridge import GateBlocked, check_gate, generate
    if not angle:
        raise RuntimeError("lo stage generate richiede --angle <nome>")
    try:
        check_gate(conn, angle)
    except GateBlocked as e:
        raise RuntimeError(str(e))
    rc = generate(angle, dry_run=False)
    if rc != 0:
        raise RuntimeError(f"generazione fallita (rc={rc})")
    n = conn.execute("""SELECT COUNT(*) c FROM variants
                        WHERE angle=? AND status='proposed'""", (angle,)).fetchone()["c"]
    return f"{n} varianti in attesa di revisione per '{angle}'"


def stage_render(conn, **kw) -> str:
    """Immagini delle varianti via Manus + GPT Image 2."""
    from variant_images import render
    done, failed = render(vid=None, status=None, force=False, dry_run=False, quiet=True)
    if done == failed == 0:
        return "nessuna variante senza immagine"
    if failed:
        raise RuntimeError(f"{failed} render falliti, {done} riusciti")
    return f"{done} immagini generate"


RUNNERS = {
    "import": stage_import,
    "assets": stage_assets,
    "classify": stage_classify,
    "analyze": stage_analyze,
    "generate": stage_generate,
    "render": stage_render,
}


# ── esecuzione ────────────────────────────────────────────────────────────────

def run_stage(stage: str, conn, **kw) -> tuple[bool, str]:
    run_id = start_run(stage, conn)
    print(f"\n▸ {stage}")
    try:
        summary = RUNNERS[stage](conn, **kw)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        finish_run(run_id, conn, "error", error=msg)
        print(f"  ✗ {msg}")
        return False, msg
    finish_run(run_id, conn, "ok", summary=summary)
    print(f"  ✓ {summary}")
    return True, summary


def run(stages: list[str], **kw) -> int:
    conn = connect()
    ensure(conn)
    orphans = reconcile_runs(conn)
    if orphans:
        print(f"({orphans} run interrotti da un processo precedente, chiusi)")
    failed = []
    for s in stages:
        ok, _ = run_stage(s, conn, **kw)
        if not ok:
            failed.append(s)
            # import fallito => assets/classify lavorerebbero su dati vecchi:
            # meglio fermarsi che produrre un risultato che sembra aggiornato.
            if s in ("import",):
                print("  ⛔ stop: gli stage successivi lavorerebbero su dati non aggiornati")
                break
    conn.close()
    if failed:
        print(f"\n{len(failed)} stage falliti: {', '.join(failed)}")
        return 1
    print(f"\n✓ pipeline completata: {' → '.join(stages)}")
    return 0


def status() -> int:
    conn = connect()
    ensure(conn)
    reconcile_runs(conn)
    tot = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    assets = conn.execute("""SELECT COUNT(*) c FROM creatives
                             WHERE asset_path IS NOT NULL AND asset_path != ''""").fetchone()["c"]
    cls = conn.execute("""SELECT COUNT(*) c FROM creatives
                          WHERE angle IS NOT NULL AND angle != ''""").fetchone()["c"]
    prop = conn.execute("SELECT COUNT(*) c FROM variants WHERE status='proposed'").fetchone()["c"]
    appr = conn.execute("SELECT COUNT(*) c FROM variants WHERE status='approved'").fetchone()["c"]

    print("STATO PIPELINE")
    print(f"  creative in DB:      {tot}")
    print(f"  asset scaricati:     {assets}/{tot}")
    print(f"  classificati:        {cls}/{tot}")
    print(f"  varianti proposte:   {prop}")
    print(f"  varianti approvate:  {appr}")
    print(f"  soglia lead:         {min_leads()} · gate {'ATTIVO' if get('generation_gate', conn) else 'DISATTIVO'}")
    print(f"  auto publish:        {'SÌ' if get('auto_publish', conn) else 'no (approvazione umana)'}")

    print("\nULTIMI RUN")
    rows = recent_runs(8, conn)
    if not rows:
        print("  nessuno")
    for r in rows:
        d = f"{r['duration_s']:.1f}s" if r["duration_s"] is not None else "—"
        icon = {"ok": "✓", "error": "✗", "running": "…"}.get(r["status"], "·")
        print(f"  {icon} {r['stage']:<10} {r['started_at']}  {d:>7}  "
              f"{(r['summary'] or r['error'] or '')[:60]}")
    conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Orchestratore pipeline creative")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("stage", choices=("all", *STAGES))
    r.add_argument("--angle", help="richiesto dallo stage generate")
    sub.add_parser("status")
    a = p.parse_args()

    if a.cmd == "status":
        return status()
    stages = list(AUTO_STAGES) if a.stage == "all" else [a.stage]
    return run(stages, angle=a.angle)


if __name__ == "__main__":
    sys.exit(main())
