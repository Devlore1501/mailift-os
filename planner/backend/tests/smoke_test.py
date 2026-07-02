"""Smoke test end-to-end del backend Planner (mock_mode, DB temporaneo).

Esegue l'intero flusso: brand → catalogo → klaviyo sync (mock) → template sync
(mock) → generazione piano → polling → edit email → rigenerazione → approvazione
→ pubblicazione (mock).

Uso:
    python tests/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("PLANNER_DATA_DIR", tempfile.mkdtemp(prefix="planner-test-"))
os.environ.pop("ANTHROPIC_API_KEY", None)  # forza mock_mode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import settings as cfg  # noqa: E402

cfg.ANTHROPIC_API_KEY = ""  # forza mock anche se .env aveva la chiave

from app.main import app  # noqa: E402

client = TestClient(app)
failures = []


def check(name: str, cond: bool, extra: str = ""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name}{(' — ' + extra) if extra else ''}")
    if not cond:
        failures.append(name)


# system
r = client.get("/api/system/status")
check("system/status", r.status_code == 200 and r.json()["mock_mode"] is True, str(r.json()))

# brand
r = client.post(
    "/api/brands",
    json={
        "name": "Bergamo Vini",
        "positioning": "Cantina DTC di qualità",
        "tone_of_voice": "Prima persona, confidenziale",
        "avatar": {"who": "Appassionato di vino 35-60", "desires": ["bere meglio"]},
        "emails_per_week": 3,
    },
)
check("create brand", r.status_code == 201, str(r.status_code))
brand_id = r.json()["id"]

r = client.get("/api/brands")
check("list brands", r.status_code == 200 and len(r.json()) == 1)

r = client.patch(f"/api/brands/{brand_id}", json={"mission": "Vino onesto"})
check("patch brand", r.status_code == 200 and r.json()["mission"] == "Vino onesto")

# catalog
r = client.post(
    f"/api/brands/{brand_id}/products",
    json={"name": "Valcalepio Rosso DOC", "category": "Rossi", "price": 14.5, "is_best_seller": True},
)
check("create product", r.status_code == 201)
product_id = r.json()["id"]

r = client.patch(f"/api/products/{product_id}", json={"price": 15.0})
check("patch product", r.status_code == 200 and r.json()["price"] == 15.0)

r = client.post(
    f"/api/brands/{brand_id}/offers",
    json={"name": "Flash sale", "code": "LUGLIO20", "discount": "-20%", "active": True},
)
check("create offer", r.status_code == 201)

r = client.post(
    f"/api/brands/{brand_id}/occasions", json={"name": "Ferragosto", "date": "2026-08-15"}
)
check("create occasion", r.status_code == 201)

# klaviyo (mock)
r = client.get(f"/api/brands/{brand_id}/klaviyo/status")
check("klaviyo status", r.status_code == 200 and r.json()["configured"] is False)

r = client.post(f"/api/brands/{brand_id}/klaviyo/sync")
check("klaviyo sync (mock)", r.status_code == 200 and r.json()["segments"], str(r.status_code))

r = client.get(f"/api/brands/{brand_id}/klaviyo/insights")
check("klaviyo insights", r.status_code == 200)

# templates (mock)
r = client.post("/api/templates/sync")
check("templates sync (mock)", r.status_code == 200 and r.json()["synced"] > 0, str(r.json()))

r = client.get("/api/templates", params={"category": "promo"})
check("templates filter", r.status_code == 200 and len(r.json()) > 0)

r = client.get("/api/templates/categories")
check("template categories", r.status_code == 200 and len(r.json()) > 0)

# notion settings
r = client.get("/api/settings/notion")
check("notion settings get", r.status_code == 200)

# plan generation
r = client.post(
    f"/api/brands/{brand_id}/plans/generate",
    json={"week_start": "2026-07-06", "num_emails": 3, "notes": "focus estate"},
)
check("generate plan (202)", r.status_code == 202, str(r.status_code))
plan_id = r.json()["id"]

r = client.post(
    f"/api/brands/{brand_id}/plans/generate", json={"week_start": "2026-07-06"}
)
check("duplicate week → 409", r.status_code == 409)

# polling fino a draft
plan = None
for _ in range(30):
    r = client.get(f"/api/plans/{plan_id}")
    plan = r.json()
    if plan["status"] != "generating":
        break
    time.sleep(0.3)
check("plan generated", plan is not None and plan["status"] == "draft", plan.get("error") or "")
check("plan has 3 emails", len(plan["emails"]) == 3, str(len(plan["emails"])))

email = plan["emails"][0]
check(
    "email card completa",
    all(
        [
            email["send_date"],
            email["send_day"],
            email["send_time"],
            email["objective"],
            email["theme"],
            email["segment"].get("name"),
            len(email["subject_variants"]) >= 2,
            email["preview_text"],
            email["body"],
        ]
    ),
)
check("template abbinato", email.get("canva_template") is not None, str(email.get("canva_template")))

# regola 80/20: con 3 email al più 1 promo/vendita
promo = sum(1 for e in plan["emails"] if e["objective"] in ("promo", "vendita"))
check("bilanciamento 80/20", promo <= 1, f"{promo} promo su 3")

# edit email
r = client.patch(
    f"/api/plans/{plan_id}/emails/{email['id']}", json={"preview_text": "Nuova preview"}
)
check("patch email → edited", r.status_code == 200 and r.json()["status"] == "edited")

# regenerate
r = client.post(
    f"/api/plans/{plan_id}/emails/{email['id']}/regenerate",
    json={"instructions": "più corta"},
)
check("regenerate email", r.status_code == 200 and r.json()["status"] == "draft")

# publish prima dell'approvazione → 409
r = client.post(f"/api/plans/{plan_id}/publish")
check("publish senza approvazione → 409", r.status_code == 409)

# approve
r = client.patch(f"/api/plans/{plan_id}", json={"status": "approved"})
check("approve plan", r.status_code == 200 and r.json()["status"] == "approved")

# publish (mock)
r = client.post(f"/api/plans/{plan_id}/publish")
check(
    "publish (mock)",
    r.status_code == 200 and r.json()["status"] == "published" and r.json()["pages"],
    str(r.json()),
)

r = client.get(f"/api/plans/{plan_id}")
check("plan published", r.json()["status"] == "published")

# delete plan + brand
r = client.delete(f"/api/plans/{plan_id}")
check("delete plan", r.status_code == 204)
r = client.delete(f"/api/brands/{brand_id}")
check("delete brand (workspace)", r.status_code == 204)

print()
if failures:
    print(f"❌ {len(failures)} test falliti: {failures}")
    sys.exit(1)
print("✅ Tutti i test smoke passati.")
