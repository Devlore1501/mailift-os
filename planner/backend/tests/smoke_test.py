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
    json={"month_start": "2026-08-01", "num_emails": 10, "notes": "focus estate"},
)
check("generate plan (202)", r.status_code == 202, str(r.status_code))
plan_id = r.json()["id"]

r = client.post(
    f"/api/brands/{brand_id}/plans/generate", json={"month_start": "2026-08-15"}
)
check("duplicate month → 409", r.status_code == 409)

# polling fino a draft
plan = None
for _ in range(30):
    r = client.get(f"/api/plans/{plan_id}")
    plan = r.json()
    if plan["status"] != "generating":
        break
    time.sleep(0.3)
check("plan generated", plan is not None and plan["status"] == "draft", plan.get("error") or "")
check("plan has 10 emails", len(plan["emails"]) == 10, str(len(plan["emails"])))

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
            email["body"] or email["blocks"],  # prosa (testuale) o scaletta (grafica)
        ]
    ),
)
check("template abbinato", email.get("canva_template") is not None, str(email.get("canva_template")))

# regola 70/20/10 su base mensile
n = len(plan["emails"])
edu = sum(1 for e in plan["emails"] if e["objective"] in ("nurturing", "storytelling"))
prod = sum(1 for e in plan["emails"] if e["objective"] == "vendita")
promo = sum(1 for e in plan["emails"] if e["objective"] == "promo")
check(
    "bilanciamento 70/20/10",
    edu >= round(0.6 * n) and promo <= max(1, round(0.15 * n)),
    f"{edu} edu / {prod} prodotto / {promo} promo su {n}",
)
dates = [e["send_date"] for e in plan["emails"]]
check("date nel mese", all(d.startswith("2026-08") for d in dates), str(dates[:3]))
check("date distinte", len(set(dates)) == len(dates))

# formati grafica/testuale bilanciati e strutture coerenti
graf = [e for e in plan["emails"] if e["format"] == "grafica"]
test = [e for e in plan["emails"] if e["format"] == "testuale"]
check("entrambi i formati presenti", len(graf) >= 2 and len(test) >= 2, f"{len(graf)}g/{len(test)}t")
check(
    "grafiche: blocks presenti, body vuoto, banner in testa",
    all(e["blocks"] and not e["body"] and e["blocks"][0]["type"] == "banner" for e in graf),
)
check(
    "grafiche: headline banner e visual compilati",
    all(e["blocks"][0]["headline"] and any(b.get("visual") for b in e["blocks"]) for e in graf),
)
check(
    "testuali: body presente, blocks vuoti, nessun template",
    all(e["body"] and not e["blocks"] and e["canva_template"] is None for e in test),
)
check("promo/vendita sempre grafiche",
      all(e["format"] == "grafica" for e in plan["emails"] if e["objective"] in ("promo", "vendita")))

# suggerimenti festività/ponti per paese
r = client.post(
    f"/api/brands/{brand_id}/occasions/suggest", json={"month": "2026-08"}
)
sugg = r.json().get("suggestions", [])
check(
    "occasions suggest (mock)",
    r.status_code == 200 and any("Ferragosto" in x["name"] for x in sugg),
    str([x["name"] for x in sugg]),
)

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

# ---- lanci & promo: sequenza dedicata nel piano
r = client.post(
    f"/api/brands/{brand_id}/launches",
    json={
        "name": "Summer Sale",
        "kind": "promo",
        "start_date": "2026-09-14",
        "end_date": "2026-09-18",
        "subject": "-20% su tutto",
    },
)
check("create launch", r.status_code == 201, str(r.status_code))
launch_id = r.json()["id"]

r = client.get(f"/api/brands/{brand_id}/launches")
check("list launches", r.status_code == 200 and len(r.json()) == 1)

r = client.patch(f"/api/launches/{launch_id}", json={"notes": "non rivelare lo sconto prima"})
check("patch launch", r.status_code == 200 and "rivelare" in r.json()["notes"])

r = client.post(
    f"/api/brands/{brand_id}/plans/generate",
    json={"month_start": "2026-09-01", "num_emails": 12},
)
check("generate plan con lancio (202)", r.status_code == 202, str(r.status_code))
plan2_id = r.json()["id"]
plan2 = None
for _ in range(30):
    plan2 = client.get(f"/api/plans/{plan2_id}").json()
    if plan2["status"] != "generating":
        break
    time.sleep(0.3)
check("plan con lancio generato", plan2 is not None and plan2["status"] == "draft",
      (plan2 or {}).get("error") or "")

seq = [e for e in plan2["emails"] if e.get("campaign")]
normal = [e for e in plan2["emails"] if not e.get("campaign")]
roles = [e["campaign"]["role"] for e in seq]
check("sequenza promo presente", len(seq) >= 4, f"{len(seq)} email in sequenza, ruoli {roles}")
check(
    "sequenza etichettata col nome della promo",
    all(e["campaign"]["name"] == "Summer Sale" for e in seq),
)
check(
    "funnel completo (5 giorni): teaser, annuncio, follow_up, last_call, final_reminder",
    {"teaser", "annuncio", "follow_up", "last_call", "final_reminder"} <= set(roles),
    str(roles),
)
check("email normali senza campaign", len(normal) > 0 and all(e["campaign"] is None for e in normal))
annuncio = next(e for e in seq if e["campaign"]["role"] == "annuncio")
final_rem = next(e for e in seq if e["campaign"]["role"] == "final_reminder")
check("annuncio grafica il giorno di inizio",
      annuncio["format"] == "grafica" and annuncio["send_date"] == "2026-09-14",
      f"{annuncio['format']} {annuncio['send_date']}")
check("final reminder testuale l'ultimo giorno, sera",
      final_rem["format"] == "testuale" and final_rem["send_date"] == "2026-09-18"
      and final_rem["send_time"] >= "18:00",
      f"{final_rem['format']} {final_rem['send_date']} {final_rem['send_time']}")
check("final reminder → segmento cliccato-non-acquirenti",
      "cliccato" in final_rem["segment"]["name"].lower(), final_rem["segment"]["name"])
campaigns = plan2.get("campaigns") or []
check(
    "strategia spiegata + proposte",
    len(campaigns) == 1
    and campaigns[0]["name"] == "Summer Sale"
    and len(campaigns[0]["strategy"]) > 40
    and len(campaigns[0]["proposals"]) >= 2,
    str(campaigns)[:120],
)

client.delete(f"/api/plans/{plan2_id}")
r = client.delete(f"/api/launches/{launch_id}")
check("delete launch", r.status_code == 204)

# estrazione profilo da documento (mock)
brand2 = client.post("/api/brands", json={"name": "Nuovo Cliente"}).json()
doc = (
    "Brand book Nuovo Cliente. Vendiamo candele artigianali profumate "
    "per chi ama la casa accogliente. Tono caldo e informale."
).encode()
r = client.post(
    f"/api/brands/{brand2['id']}/extract-profile",
    files=[("files", ("brandbook.txt", doc, "text/plain"))],
)
check(
    "extract-profile (mock)",
    r.status_code == 200 and r.json()["description"],
    str(r.status_code),
)
r = client.post(
    f"/api/brands/{brand2['id']}/extract-profile?apply=true",
    files=[("files", ("brandbook.txt", doc, "text/plain"))],
)
check("extract-profile apply", r.status_code == 200 and r.json()["applied"] is True)
r = client.get(f"/api/brands/{brand2['id']}")
check("profilo applicato", "candele" in r.json()["description"].lower(), r.json()["description"][:60])
r = client.post(
    f"/api/brands/{brand2['id']}/extract-profile",
    files=[("files", ("virus.exe", b"x", "application/octet-stream"))],
)
check("formato non supportato → 415", r.status_code == 415)
client.delete(f"/api/brands/{brand2['id']}")

# set di template Canva (elenco tipi × varianti, formato Notion di Mailift)
r = client.get("/api/templates/set")
check("canva set vuoto", r.status_code == 200 and r.json()["canva_file_url"] == "")

notion_text = """## Tutte le voci (New database)

- About x3
- Flash Sale x3
- FAQ x3
- How-to? x3
- Product Features x3
- Recommendations x
- Special Day x3
"""
set_payload = {
    "canva_file_url": "https://www.canva.com/design/TESTFILE/edit",
    "entries_text": notion_text,
}
r = client.put("/api/templates/set", json=set_payload)
out = r.json()
check(
    "canva set apply (7 tipi × 3 = 21)",
    r.status_code == 200 and out["template_count"] == 21,
    str(out),
)
by_name = {e["name"]: e["category"] for e in out.get("entries", [])}
check(
    "categorie auto-assegnate",
    by_name.get("Flash Sale") == "promo"
    and by_name.get("How-to?") == "educativo"
    and by_name.get("About") == "storytelling"
    and by_name.get("Special Day") == "stagionale",
    str(by_name),
)

r = client.get("/api/templates", params={"category": "educativo"})
check(
    "canva set espanso per categoria",
    r.status_code == 200
    and len(r.json()) == 6  # FAQ x3 + How-to? x3
    and r.json()[0]["canva_url"].startswith(set_payload["canva_file_url"] + "#"),
    str(len(r.json())),
)

r = client.get("/api/templates/set")
check(
    "canva set persistito",
    r.json()["canva_file_url"] == set_payload["canva_file_url"]
    and r.json()["template_count"] == 21,
    str(r.json()["template_count"]),
)

r = client.put(
    "/api/templates/set",
    json={
        "canva_file_url": "",
        "entries": [
            {"name": "About", "count": 3},
            {"name": "about", "count": 2},
        ],
    },
)
check("canva set duplicato → 422", r.status_code == 422, str(r.status_code))

r = client.put("/api/templates/set", json={"canva_file_url": "", "entries": []})
check("canva set vuoto → 422", r.status_code == 422)

# deep-link alla pagina del file Canva
r = client.put("/api/templates/set", json=set_payload)
tpl = client.get("/api/templates").json()
check(
    "deep-link pagina Canva",
    all(t["canva_url"].endswith(f"#{i+1}") for i, t in enumerate(
        sorted(tpl, key=lambda t: int(t["canva_url"].rsplit("#", 1)[1]))
    )),
    tpl[0]["canva_url"] if tpl else "",
)

# anteprime: upload immagini numerate → match per pagina
png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
r = client.post(
    "/api/templates/previews",
    files=[
        ("files", ("Canva Templates - 1.png", png, "image/png")),
        ("files", ("Canva Templates - 5.png", png, "image/png")),
    ],
)
check(
    "upload anteprime",
    r.status_code == 200 and r.json()["saved"] == 2 and r.json()["matched"] == 2,
    str(r.json()),
)
r = client.get("/api/templates/previews/5")
check("serve anteprima", r.status_code == 200)
r = client.get("/api/templates/previews/99")
check("anteprima mancante → 404", r.status_code == 404)
with_previews = [t for t in client.get("/api/templates").json() if t["preview_url"]]
check(
    "preview_url sui template",
    len(with_previews) == 2
    and with_previews[0]["preview_url"].startswith("/api/templates/previews/"),
    str([t["name"] for t in with_previews]),
)

# la sync mock rimpiazza la libreria (una sorgente attiva alla volta)
r = client.post("/api/templates/sync")
check(
    "sync rimpiazza il set",
    r.status_code == 200
    and client.get("/api/templates/set").json()["template_count"] == 0,
)

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
