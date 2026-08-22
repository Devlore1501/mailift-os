#!/usr/bin/env python3
"""
Dashboard di configurazione e controllo della pipeline creative.

Server locale: legge/scrive la config, lancia gli stage, mostra lo storico dei
run e permette di approvare o rifiutare le varianti proposte.

Gli stage girano in un thread singolo con lock: due import in parallelo si
pesterebbero sul DB e sul rate limit di Meta.

Avvio:
  python tools/control_server.py            # http://127.0.0.1:8848
  python tools/control_server.py --port 9000
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

import pipeline
import pipeline_config
from creative_db import EVENT_CLASSES, connect, min_leads

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "control_dashboard.html.tpl"

app = FastAPI(title="Mailift · Controllo pipeline creative")

# Un solo stage alla volta: il DB e il rate limit Meta non sono rientranti.
_lock = threading.Lock()
_current: dict | None = None


class ConfigPatch(BaseModel):
    key: str
    value: str


class RunRequest(BaseModel):
    stage: str
    angle: str | None = None


class Decision(BaseModel):
    status: str
    note: str | None = None


def _angles() -> list[dict]:
    from manus_bridge import angle_stats
    conn = connect()
    pipeline_config.ensure(conn)
    try:
        return angle_stats(conn)
    finally:
        conn.close()


def _state() -> dict:
    conn = connect()
    pipeline_config.ensure(conn)
    try:
        one = lambda q: conn.execute(q).fetchone()["c"]
        tot = one("SELECT COUNT(*) c FROM creatives")
        counts = {
            "creatives": tot,
            "assets": one("SELECT COUNT(*) c FROM creatives WHERE asset_path IS NOT NULL AND asset_path != ''"),
            "classified": one("SELECT COUNT(*) c FROM creatives WHERE angle IS NOT NULL AND angle != ''"),
            "classify_errors": one("SELECT COUNT(*) c FROM creatives WHERE classify_error IS NOT NULL"),
            "proposed": one("SELECT COUNT(*) c FROM variants WHERE status='proposed'"),
            "approved": one("SELECT COUNT(*) c FROM variants WHERE status='approved'"),
            "rejected": one("SELECT COUNT(*) c FROM variants WHERE status='rejected'"),
            "rendered": one("""SELECT COUNT(*) c FROM variants
                               WHERE asset_path IS NOT NULL AND asset_path != ''"""),
        }
        variants = [dict(r) for r in conn.execute(
            "SELECT * FROM variants ORDER BY id DESC LIMIT 50")]
        for v in variants:
            try:
                v["extra"] = json.loads(v["rationale"] or "{}")
            except json.JSONDecodeError:
                v["extra"] = {}
        runs = pipeline_config.recent_runs(12, conn)
        cfg = pipeline_config.all_config(conn)
    finally:
        conn.close()

    return {
        "counts": counts,
        "config": cfg,
        "runs": runs,
        "angles": _angles(),
        "variants": variants,
        "threshold": min_leads(),
        "stages": list(pipeline.STAGES),
        "auto_stages": list(pipeline.AUTO_STAGES),
        "current": _current,
        "now": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }


def _worker(stage: str, angle: str | None) -> None:
    global _current
    conn = connect()
    pipeline_config.ensure(conn)
    try:
        stages = list(pipeline.AUTO_STAGES) if stage == "all" else [stage]
        for s in stages:
            _current = {"stage": s, "started_at": datetime.now().isoformat(timespec="seconds")}
            ok, _ = pipeline.run_stage(s, conn, angle=angle)
            if not ok and s == "import":
                break
    except Exception:
        traceback.print_exc()
    finally:
        _current = None
        conn.close()
        _lock.release()


def _render_worker(vid: int) -> None:
    """Render di una singola variante: passa dal lock come ogni altro stage."""
    global _current
    conn = connect()
    pipeline_config.ensure(conn)
    run_id = pipeline_config.start_run(f"render:{vid}", conn)
    _current = {"stage": f"render:{vid}",
                "started_at": datetime.now().isoformat(timespec="seconds")}
    try:
        from variant_images import render
        done, failed = render(vid=vid, status=None, force=True, dry_run=False, quiet=True)
        if failed:
            row = conn.execute("SELECT render_error FROM variants WHERE id=?", (vid,)).fetchone()
            pipeline_config.finish_run(run_id, conn, "error",
                                       error=(row["render_error"] if row else "render fallito"))
        else:
            pipeline_config.finish_run(run_id, conn, "ok", summary=f"immagine variante {vid}")
    except Exception as e:
        traceback.print_exc()
        pipeline_config.finish_run(run_id, conn, "error", error=f"{type(e).__name__}: {e}")
    finally:
        _current = None
        conn.close()
        _lock.release()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


@app.get("/api/state")
def api_state() -> dict:
    return _state()


@app.post("/api/config")
def api_config(p: ConfigPatch) -> dict:
    try:
        pipeline_config.set_(p.key, p.value)
    except KeyError as e:
        raise HTTPException(400, str(e))
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(400, f"valore non valido per {p.key}: {e}")
    return {"key": p.key, "value": pipeline_config.get(p.key)}


@app.post("/api/config/reset")
def api_config_reset(p: ConfigPatch) -> dict:
    try:
        pipeline_config.reset(p.key)
    except KeyError as e:
        raise HTTPException(400, str(e))
    return {"key": p.key, "value": pipeline_config.get(p.key)}


@app.post("/api/run")
def api_run(r: RunRequest) -> dict:
    if r.stage != "all" and r.stage not in pipeline.STAGES:
        raise HTTPException(400, f"stage sconosciuto: {r.stage}")
    if r.stage == "generate" and not r.angle:
        raise HTTPException(400, "lo stage generate richiede un angolo")
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, f"c'è già uno stage in corso: {(_current or {}).get('stage')}")
    threading.Thread(target=_worker, args=(r.stage, r.angle), daemon=True).start()
    return {"started": r.stage, "angle": r.angle}


@app.post("/api/variants/{vid}/render")
def api_variant_render(vid: int) -> dict:
    conn = connect()
    try:
        row = conn.execute("SELECT status FROM variants WHERE id=?", (vid,)).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, "variante non trovata")
    if row["status"] == "rejected":
        raise HTTPException(400, "variante rifiutata: generare l'immagine sarebbe spesa buttata")
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, f"c'è già uno stage in corso: {(_current or {}).get('stage')}")
    threading.Thread(target=_render_worker, args=(vid,), daemon=True).start()
    return {"started": "render", "variant": vid}


@app.get("/api/variants/{vid}/image")
def api_variant_image(vid: int):
    conn = connect()
    try:
        row = conn.execute("SELECT asset_path FROM variants WHERE id=?", (vid,)).fetchone()
    finally:
        conn.close()
    if not row or not row["asset_path"]:
        raise HTTPException(404, "questa variante non ha ancora un'immagine")
    # Il path arriva dal DB, non dall'utente, ma resta confinato sotto data/.
    path = (ROOT / row["asset_path"]).resolve()
    if not path.is_file() or not path.is_relative_to((ROOT / "data").resolve()):
        raise HTTPException(404, "file immagine non trovato")
    return FileResponse(path)


@app.post("/api/variants/{vid}/decide")
def api_decide(vid: int, d: Decision) -> dict:
    if d.status not in ("approved", "rejected"):
        raise HTTPException(400, "stato ammesso: approved | rejected")
    conn = connect()
    pipeline_config.ensure(conn)
    try:
        cur = conn.execute(
            """UPDATE variants SET status=?, decided_at=?, decided_note=?
               WHERE id=? AND status='proposed'""",
            (d.status, datetime.now().isoformat(timespec="seconds"), d.note, vid))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(404, "variante non trovata o già decisa")
    finally:
        conn.close()
    return {"id": vid, "status": d.status}


def main() -> int:
    p = argparse.ArgumentParser(description="Dashboard di controllo pipeline")
    p.add_argument("--port", type=int, default=8848)
    p.add_argument("--host", default="127.0.0.1")
    a = p.parse_args()
    conn = connect()
    orphans = pipeline_config.reconcile_runs(conn)
    conn.close()
    if orphans:
        print(f"{orphans} run interrotti da un processo precedente: chiusi.")

    import uvicorn
    print(f"Controllo pipeline: http://{a.host}:{a.port}")
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
