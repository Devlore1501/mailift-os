"""Smoke test Email Planner backend (TestClient, DB temporaneo)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# DB pulito: punta il modulo a un file temporaneo prima dell'import
import tempfile
_db = Path(tempfile.gettempdir()) / "email_planner_test.db"
if _db.exists():
    _db.unlink()

import app.main as planner  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

planner.engine = create_engine(f"sqlite:///{_db}", connect_args={"check_same_thread": False})
planner.SessionLocal = sessionmaker(bind=planner.engine, autoflush=False)

from fastapi.testclient import TestClient  # noqa: E402

PASSED = 0


def check(name, cond, extra=""):
    global PASSED
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        sys.exit(1)
    PASSED += 1


with TestClient(planner.app) as client:
    check("health", client.get("/api/health").status_code == 200)

    r = client.get("/api/clients")
    check("seed clienti retainer", r.status_code == 200 and len(r.json()) == 3,
          ", ".join(c["name"] for c in r.json()))
    bergamo = next(c for c in r.json() if c["name"] == "Bergamo Vini")
    check("programma Bergamo Vini nel seed", "sabato" in (bergamo["program_notes"] or ""))

    # crea campagna
    r = client.post("/api/campaigns", json={"client_id": bergamo["id"], "title": "Flash sale giugno", "type": "flash_sale"})
    check("crea campagna", r.status_code == 201)
    cid = r.json()["id"]

    r = client.post("/api/campaigns", json={"title": "senza cliente"})
    check("campagna senza cliente rifiutata", r.status_code == 422)

    # guardrail: programmata richiede la data
    r = client.post(f"/api/campaigns/{cid}/status", json={"status": "programmata"})
    check("programmata senza data bloccata", r.status_code == 422, r.json()["detail"][:50])

    when = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    client.patch(f"/api/campaigns/{cid}", json={"scheduled_at": when, "subject": "Ultimi 3 giorni"})
    r = client.post(f"/api/campaigns/{cid}/status", json={"status": "programmata"})
    check("programmata con data ok", r.status_code == 200)

    r = client.post(f"/api/campaigns/{cid}/status", json={"status": "inviata"})
    check("inviata: sent_at auto", r.status_code == 200 and r.json()["sent_at"])

    r = client.patch(f"/api/campaigns/{cid}", json={"open_rate_pct": 42.5, "ctr_pct": 3.1, "revenue": 850})
    check("risultati post-invio salvati", r.status_code == 200 and r.json()["open_rate_pct"] == 42.5)

    # filtri
    r = client.get("/api/campaigns", params={"client_id": bergamo["id"], "status": "inviata"})
    check("filtri cliente+status", len(r.json()) == 1)
    r = client.get("/api/campaigns", params={
        "scheduled_from": datetime.now(timezone.utc).isoformat(),
        "scheduled_to": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    })
    check("filtro calendario", len(r.json()) == 1)

    r = client.delete(f"/api/campaigns/{cid}")
    check("elimina campagna", r.status_code == 204)

print(f"\n✅ Smoke test Email Planner: {PASSED} check passati")
