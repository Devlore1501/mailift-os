"""Smoke test E2E del backend Content Dashboard (senza server esterno: TestClient).

Esecuzione:
    cd content-dashboard/backend
    CONTENT_DASHBOARD_DB=.tmp/test_e2e.db ../../.venv/bin/python tests/smoke_test_e2e.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# DB pulito per ogni run
_test_db = Path(tempfile.gettempdir()) / "content_dashboard_test.db"
if _test_db.exists():
    _test_db.unlink()
os.environ["CONTENT_DASHBOARD_DB"] = str(_test_db)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASSED = 0


def check(name: str, condition: bool, extra: str = ""):
    global PASSED
    status = "OK " if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {extra}" if extra else ""))
    if not condition:
        sys.exit(1)
    PASSED += 1


def auth(token):
    return {"Authorization": f"Bearer {token}"}


with TestClient(app) as client:
    # 1. health
    r = client.get("/api/health")
    check("health", r.status_code == 200 and r.json()["db_ok"])

    # 2. login admin di default
    r = client.post("/api/auth/login", json={"email": "lorenzo@mailift.it", "password": "mailift-admin"})
    check("login admin", r.status_code == 200)
    admin_token = r.json()["token"]

    r = client.post("/api/auth/login", json={"email": "lorenzo@mailift.it", "password": "sbagliata"})
    check("login con password errata rifiutato", r.status_code == 401)

    r = client.get("/api/kpi/overview")
    check("API senza token rifiutata (NFR-04)", r.status_code == 401)

    # 3. crea editor e contributor
    r = client.post("/api/users", headers=auth(admin_token),
                    json={"name": "Anna AM", "email": "anna@mailift.it", "password": "password123", "role": "editor"})
    check("crea utente editor", r.status_code == 201)
    r = client.post("/api/users", headers=auth(admin_token),
                    json={"name": "Fabio Freelance", "email": "fabio@mailift.it", "password": "password123", "role": "contributor"})
    check("crea utente contributor", r.status_code == 201)

    editor_token = client.post("/api/auth/login", json={"email": "anna@mailift.it", "password": "password123"}).json()["token"]
    contrib_token = client.post("/api/auth/login", json={"email": "fabio@mailift.it", "password": "password123"}).json()["token"]

    r = client.post("/api/users", headers=auth(editor_token),
                    json={"name": "X", "email": "x@mailift.it", "password": "password123", "role": "editor"})
    check("editor non può creare utenti", r.status_code == 403)

    # 4. M1: idea madre + 4 figli (FR-M1-01/02/03)
    r = client.post("/api/ideas", headers=auth(editor_token),
                    json={"title": "Il carrello abbandonato ti costa 3k/mese", "angle": "Quantificare il leak",
                          "pillar": "revenue_leak"})
    check("crea idea madre", r.status_code == 201)
    idea_id = r.json()["id"]

    r = client.post(f"/api/ideas/{idea_id}/children", headers=auth(editor_token), json={"children": [
        {"surface": "reel", "format": "talking_head"},
        {"surface": "carousel", "format": "dati_grafici"},
        {"surface": "story", "format": "qna"},
        {"surface": "reel", "format": "mito_sfatato"},
    ]})
    check("genera 4 figli dall'idea madre", r.status_code == 201 and len(r.json()["contents"]) == 4,
          f"{len(r.json().get('contents', []))} figli")
    child_ids = [c["id"] for c in r.json()["contents"]]
    first = child_ids[0]

    # figli ereditano il pillar
    r = client.get(f"/api/contents/{first}", headers=auth(contrib_token))
    check("figlio eredita pillar dall'idea", r.json()["pillar"] == "revenue_leak")

    # 5. Contributor: script sì, critic_score no (FR-M1-09 + ruoli)
    r = client.patch(f"/api/contents/{first}", headers=auth(contrib_token),
                     json={"script": "Script di prova", "hook": "Stai perdendo 3k al mese"})
    check("contributor modifica script/hook", r.status_code == 200)
    r = client.patch(f"/api/contents/{first}", headers=auth(contrib_token), json={"critic_score": 50})
    check("contributor NON può settare critic_score", r.status_code == 403)
    r = client.post(f"/api/contents/{first}/status", headers=auth(contrib_token), json={"status": "script"})
    check("contributor muove in Script", r.status_code == 200)
    r = client.post(f"/api/contents/{first}/status", headers=auth(contrib_token), json={"status": "scheduled"})
    check("contributor NON può programmare", r.status_code == 403)

    # 6. Gate Critico (FR-M1-05): score 35 blocca, 41 passa
    r = client.post(f"/api/contents/{first}/status", headers=auth(editor_token), json={"status": "scheduled"})
    check("gate: senza score niente Programmato", r.status_code == 422, r.json().get("detail", "")[:60])
    client.patch(f"/api/contents/{first}", headers=auth(editor_token), json={"critic_score": 35})
    r = client.post(f"/api/contents/{first}/status", headers=auth(editor_token), json={"status": "scheduled"})
    check("gate: score 35 < 38 bloccato con spiegazione",
          r.status_code == 422 and "35" in r.json()["detail"], r.json()["detail"][:70])
    client.patch(f"/api/contents/{first}", headers=auth(editor_token), json={"critic_score": 41})
    r = client.post(f"/api/contents/{first}/status", headers=auth(editor_token), json={"status": "scheduled"})
    check("gate: score 41 passa", r.status_code == 200 and r.json()["status"] == "scheduled")

    # 7. pubblica + metriche manuali (FR-M2-01) con rate calcolati
    r = client.post(f"/api/contents/{first}/status", headers=auth(editor_token), json={"status": "published"})
    check("pubblica contenuto (published_at auto)", r.status_code == 200 and r.json()["published_at"])
    r = client.post(f"/api/contents/{first}/metrics", headers=auth(editor_token), json={
        "views": 10000, "likes": 400, "avg_retention_pct": 68, "hook_retention_pct": 82,
        "saves": 300, "shares": 120, "icp_comments": 12, "non_icp_comments": 3,
        "dm_keyword_triggers": 40, "fhs_clicks": 25, "fhs_purchases": 5,
    })
    m = r.json()
    check("metrica manuale con rate calcolati",
          r.status_code == 201 and abs(m["save_rate"] - 0.03) < 1e-9 and abs(m["icp_ratio"] - 0.8) < 1e-9
          and abs(m["dm_fhs_rate"] - 0.125) < 1e-9)

    # 8. CSV import (FR-M2-02): pubblica il secondo figlio e importa via external_url
    second = child_ids[1]
    client.patch(f"/api/contents/{second}", headers=auth(editor_token),
                 json={"critic_score": 44, "external_url": "https://instagram.com/reel/abc123"})
    client.post(f"/api/contents/{second}/status", headers=auth(editor_token), json={"status": "scheduled"})
    client.post(f"/api/contents/{second}/status", headers=auth(editor_token), json={"status": "published"})
    csv_data = (
        "url,visualizzazioni,retention,salvataggi\n"
        "https://instagram.com/reel/abc123,5000,55.5,90\n"
        "https://instagram.com/reel/inesistente,100,10,1\n"
    )
    r = client.post("/api/metrics/import", headers=auth(editor_token),
                    files={"file": ("export.csv", csv_data.encode(), "text/csv")},
                    data={"mapping": '{"visualizzazioni": "views", "retention": "avg_retention_pct", "salvataggi": "saves"}',
                          "match_field": "external_url", "match_column": "url"})
    body = r.json()
    check("import CSV: 1 riga importata, 1 non matchata",
          r.status_code == 200 and body["imported"] == 1 and len(body["unmatched"]) == 1, str(body))

    # 9. KPI overview (FR-M2-04/05)
    r = client.get("/api/kpi/overview", headers=auth(editor_token))
    ov = r.json()
    check("KPI overview: primari + vanity + trend",
          r.status_code == 200 and ov["n_published"] == 2 and ov["primary"]["avg_retention_pct"] is not None
          and ov["secondary"]["views"] == 15000 and len(ov["trend"]) >= 1)
    check("winner detection: retention 68 > 65", first in ov["winner_ids"])

    # 10. mix pillar (FR-M1-08): tutto revenue_leak → alert su scostamento
    r = client.get("/api/kpi/pillar-mix", headers=auth(editor_token))
    mix = r.json()
    rl = next(row for row in mix["rows"] if row["pillar"] == "revenue_leak")
    check("mix pillar: 100% revenue_leak vs 30% target → alert",
          rl["real_pct"] == 100.0 and rl["alert"] and len(mix["alerts"]) >= 1, mix["alerts"][0])

    # 11. kill flag (FR-M2-09): 5 post pubblicati stesso format con retention < 40
    for i in range(5):
        rc = client.post("/api/contents", headers=auth(editor_token),
                         json={"surface": "reel", "format": "reaction", "pillar": "proof"})
        cid = rc.json()["id"]
        client.patch(f"/api/contents/{cid}", headers=auth(editor_token), json={"critic_score": 40})
        client.post(f"/api/contents/{cid}/status", headers=auth(editor_token), json={"status": "scheduled"})
        client.post(f"/api/contents/{cid}/status", headers=auth(editor_token), json={"status": "published"})
        client.post(f"/api/contents/{cid}/metrics", headers=auth(editor_token),
                    json={"views": 1000, "avg_retention_pct": 30 + i})
    r = client.get("/api/kpi/breakdown?by=format", headers=auth(editor_token))
    rows = {row["key"]: row for row in r.json()["rows"]}
    check("breakdown per format", r.status_code == 200 and "reaction" in rows)
    check("kill flag: format reaction retention ~32 dopo 5 post", rows["reaction"]["kill_flag"],
          f"retention={rows['reaction']['avg_retention_pct']}")
    check("campione insufficiente segnalato (talking_head 1 post)",
          rows["talking_head"]["insufficient_sample"])
    r = client.get("/api/kpi/breakdown?by=pillar", headers=auth(editor_token))
    check("breakdown per pillar", r.status_code == 200 and len(r.json()["rows"]) >= 2)

    # 12. M3: fonti (admin only) + fetch RSS locale + coda review
    r = client.post("/api/sources", headers=auth(editor_token),
                    json={"type": "rss", "url": "x", "label": "X"})
    check("editor NON può creare fonti", r.status_code == 403)

    rss_file = Path(tempfile.gettempdir()) / "test_feed.xml"
    rss_file.write_text("""<?xml version="1.0"?><rss version="2.0"><channel>
      <title>Test Feed</title><link>http://example.com</link><description>t</description>
      <item><title>Shopify lancia nuove API checkout</title><link>http://example.com/a1</link>
        <description>Novità per gli store DTC italiani</description></item>
      <item><title>Klaviyo aumenta i prezzi</title><link>http://example.com/a2</link>
        <description>Impatto sui flussi email</description></item>
    </channel></rss>""")
    r = client.post("/api/sources", headers=auth(admin_token),
                    json={"type": "rss", "url": str(rss_file), "label": "Feed di test"})
    check("admin crea fonte RSS", r.status_code == 201)
    r = client.post("/api/sources", headers=auth(admin_token),
                    json={"type": "rss", "url": "/percorso/inesistente.xml", "label": "Fonte rotta"})
    broken_source = r.json()["id"]

    r = client.post("/api/idea-engine/fetch", headers=auth(editor_token))
    fetch = r.json()
    check("fetch fonti: 2 item nuovi, dedup pronto", r.status_code == 200 and fetch["total_added"] == 2)
    broken = next(s for s in fetch["sources"] if s["source_id"] == broken_source)
    check("fonte rotta fallisce con grazia (NFR-08)", broken["error"] is not None and fetch["total_added"] == 2)

    r = client.post("/api/idea-engine/fetch", headers=auth(editor_token))
    check("secondo fetch: dedup, 0 nuovi item", r.json()["total_added"] == 0)

    r = client.post("/api/idea-engine/synthesize", headers=auth(editor_token))
    synth = r.json()
    if synth.get("error"):
        check("sintesi AI senza chiave: errore gestito, item preservati",
              "ANTHROPIC_API_KEY" in synth["error"])
    else:
        check("sintesi AI: proposte generate", synth["proposals_created"] >= 0)

    # coda review (FR-M3-04): approva una proposta → idea madre utilizzabile
    from app.db import SessionLocal
    from app.models import Idea
    _db = SessionLocal()
    _db.add(Idea(title="Proposta AI di test", angle="test", pillar="educational",
                 status="proposed", origin="ai", relevance_score=8))
    _db.commit()
    _db.close()
    r = client.get("/api/ideas?status=proposed", headers=auth(editor_token))
    check("coda review: proposte ordinate per rilevanza", r.status_code == 200 and len(r.json()) == 1)
    proposal_id = r.json()[0]["id"]
    r = client.patch(f"/api/ideas/{proposal_id}", headers=auth(editor_token), json={"status": "approved"})
    check("approva proposta → idea madre", r.status_code == 200 and r.json()["status"] == "approved")
    r = client.post(f"/api/ideas/{proposal_id}/children", headers=auth(editor_token),
                    json={"children": [{"surface": "reel"}]})
    check("idea approvata genera figli", r.status_code == 201)

    # 13. impostazioni (FR-X-03)
    r = client.put("/api/config/pillar-targets", headers=auth(admin_token),
                   json={"targets": {"revenue_leak": 50, "proof": 20, "educational": 20, "contrarian": 5, "backstage": 5}})
    check("admin aggiorna target pillar", r.status_code == 200)
    r = client.put("/api/config/pillar-targets", headers=auth(admin_token),
                   json={"targets": {"revenue_leak": 90}})
    check("target che non sommano a 100 rifiutati", r.status_code == 422)
    r = client.put("/api/config/settings", headers=auth(editor_token), json={"values": {"critic_gate_min": "10"}})
    check("editor NON può cambiare le soglie", r.status_code == 403)
    r = client.put("/api/config/settings", headers=auth(admin_token), json={"values": {"critic_gate_min": "45"}})
    check("admin alza il gate a 45", r.status_code == 200)
    third = child_ids[2]
    client.patch(f"/api/contents/{third}", headers=auth(editor_token), json={"critic_score": 41})
    r = client.post(f"/api/contents/{third}/status", headers=auth(editor_token), json={"status": "scheduled"})
    check("gate configurabile: 41 < 45 ora bloccato", r.status_code == 422)

    # 14. calendario: filtro per scheduled range (FR-M1-06)
    now = datetime.now(timezone.utc)
    client.patch(f"/api/contents/{third}", headers=auth(editor_token),
                 json={"scheduled_at": (now + timedelta(days=2)).isoformat()})
    r = client.get("/api/contents", headers=auth(editor_token),
                   params={"scheduled_from": now.isoformat(),
                           "scheduled_to": (now + timedelta(days=7)).isoformat()})
    check("filtro calendario per data programmazione", r.status_code == 200 and len(r.json()) == 1)

    # 15. activity log (FR-X-04)
    r = client.get("/api/activity", headers=auth(editor_token))
    check("activity log popolato", r.status_code == 200 and len(r.json()) > 5)

print(f"\n✅ Smoke test E2E completato: {PASSED} check passati")
