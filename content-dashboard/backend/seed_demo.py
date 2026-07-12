"""Popola il DB con dati demo realistici per vedere la dashboard piena.

Esecuzione (dal root del repo, sovrascrive nulla: aggiunge solo se DB quasi vuoto):
    cd content-dashboard/backend && ../../.venv/bin/python seed_demo.py
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import Base, SessionLocal, engine
from app.models import Content, Idea, Metric
from app.seed import run_seed

random.seed(42)

IDEAS = [
    ("Il tuo carrello abbandonato vale 3.000€/mese", "revenue_leak", "Quantificare in euro il leak medio di uno store da 50k/mese"),
    ("Da 0 a 12k€ di revenue email in 60 giorni", "proof", "Case study Kalishoes: setup flussi + campagne"),
    ("I 5 flussi Klaviyo che ogni store deve avere", "educational", "Checklist operativa, uno per slide"),
    ("Le email non sono morte. Il tuo modo di scriverle sì.", "contrarian", "Contro il 'le email non le legge nessuno'"),
    ("Come lavoriamo un nuovo cliente nei primi 7 giorni", "backstage", "Dietro le quinte onboarding Mailift"),
    ("Il 30% del fatturato che Shopify ti nasconde", "revenue_leak", "Revenue attribution: quanto viene dall'email davvero"),
    ("Perché il pop-up sconto 10% ti sta costando margine", "contrarian", "Alternative al pop-up sconto standard"),
    ("Flow Health Score: cosa misura davvero", "educational", "Spiegazione del FHS €37 senza vendere"),
]

FORMATS_POOL = ["talking_head", "dati_grafici", "caso_studio", "lista_errori",
                "mito_sfatato", "tutorial", "storytelling", "qna"]
SURFACE_BY_INDEX = ["reel", "carousel", "story", "reel"]

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    run_seed(db)
    if db.query(Content).count() > 5:
        print("DB già popolato, non tocco nulla.")
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)  # UTC naive come il resto del DB

    # le ultime 2 idee restano in lavorazione: pipeline popolata su tutti gli stati
    PIPELINE_STATES = ["idea", "script", "production", "critic", "scheduled"]
    in_progress_ideas = {IDEAS[-1][0]: 0, IDEAS[-2][0]: 1}

    week = 0
    for title, pillar, angle in IDEAS:
        idea = Idea(title=title, angle=angle, pillar=pillar, status="approved",
                    origin="manual", created_at=now - timedelta(days=56 - week * 7))
        db.add(idea)
        db.flush()
        for j in range(4):
            fmt = random.choice(FORMATS_POOL)
            published = now - timedelta(days=54 - week * 7 - j, hours=random.randint(0, 12))
            if title in in_progress_ideas:
                # idea in lavorazione: figli distribuiti sulla pipeline, non pubblicati
                state = PIPELINE_STATES[(in_progress_ideas[title] + j) % len(PIPELINE_STATES)]
                db.add(Content(
                    idea_id=idea.id, surface=SURFACE_BY_INDEX[j], format=fmt, pillar=pillar,
                    platform="instagram", hook=f"Hook: {title[:40]}…",
                    script=f"Script demo per {title}" if state != "idea" else None,
                    cta_keyword="FLOW",
                    critic_score=random.randint(38, 46) if state == "scheduled" else (
                        random.randint(30, 37) if state == "critic" else None),
                    status=state,
                    scheduled_at=now + timedelta(days=2 + j) if state == "scheduled" else None,
                    created_at=now - timedelta(days=3),
                ))
                continue
            is_published = True
            content = Content(
                idea_id=idea.id, surface=SURFACE_BY_INDEX[j], format=fmt, pillar=pillar,
                platform=random.choice(["instagram", "instagram", "tiktok"]),
                hook=f"Hook: {title[:40]}…", script=f"Script demo per {title}",
                cta_keyword="FLOW", critic_score=random.randint(38, 48),
                status="published",
                scheduled_at=published, published_at=published,
                external_url=f"https://instagram.com/reel/demo{idea.id}{j}",
                created_at=published - timedelta(days=5),
            )
            db.add(content)
            db.flush()
            if is_published:
                base_views = random.randint(2000, 25000)
                # il format 'reaction' non esiste nel pool: i kill flag emergono da retention basse
                retention = random.uniform(35, 75) if fmt != "caso_studio" else random.uniform(55, 80)
                icp = random.randint(3, 25)
                db.add(Metric(
                    content_id=content.id, captured_at=published + timedelta(days=2),
                    views=base_views, likes=int(base_views * random.uniform(0.02, 0.08)),
                    avg_retention_pct=round(retention, 1),
                    hook_retention_pct=round(min(95, retention + random.uniform(8, 20)), 1),
                    rewatch_rate=round(random.uniform(0.05, 0.25), 3),
                    saves=int(base_views * random.uniform(0.005, 0.04)),
                    shares=int(base_views * random.uniform(0.003, 0.02)),
                    comments=random.randint(4, 60),
                    icp_comments=icp, non_icp_comments=random.randint(0, 12),
                    dm_keyword_triggers=random.randint(0, 30),
                    fhs_clicks=random.randint(0, 20), fhs_purchases=random.randint(0, 4),
                ))
        week += 1

    # proposte AI in coda review
    for title, pillar, relevance in [
        ("Shopify Editions: 3 novità che toccano il tuo store", "educational", 8),
        ("iOS 19 e apertura email: cosa cambia per i report", "contrarian", 7),
        ("Klaviyo alza i prezzi: come tagliare i contatti inutili", "revenue_leak", 9),
    ]:
        db.add(Idea(title=title, pillar=pillar, status="proposed", origin="ai",
                    relevance_score=relevance, angle="Proposta demo dell'Idea Engine",
                    hook_draft=f"Bozza hook: {title}"))

    # le fonti arrivano già dal catalogo consigliato via run_seed()
    db.commit()
    print(f"Seed demo: {db.query(Idea).count()} idee, {db.query(Content).count()} contenuti, "
          f"{db.query(Metric).count()} snapshot metriche.")
    db.close()


if __name__ == "__main__":
    main()
