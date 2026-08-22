#!/usr/bin/env python3
"""
Genera la dashboard HTML del Creative DB.

L'HTML e' un artefatto rigenerabile: la fonte di verita' resta il DB, quindi
si rilancia dopo ogni import invece di modificare la pagina a mano.

CLI:
  python tools/creative_dashboard.py
  python tools/creative_dashboard.py --output .tmp/creative_dashboard.html
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from creative_db import (CLASS_NOTE, DB_PATH, EVENT_CLASSES, _event_label, connect,
                         migrate, min_leads)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / ".tmp" / "creative_dashboard.html"
TEMPLATE = Path(__file__).resolve().parent / "creative_dashboard.html.tpl"


def collect() -> dict:
    conn = connect()
    migrate(conn)

    classes = []
    for r in conn.execute("""
        SELECT a.optimization_goal, a.custom_event_type,
               COUNT(DISTINCT c.creative_id) n,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        GROUP BY a.optimization_goal, a.custom_event_type
        ORDER BY spend DESC
    """):
        ev = _event_label(r)
        classes.append({
            "event": ev,
            "goal": r["optimization_goal"] or "—",
            "klass": EVENT_CLASSES.get(ev, "?"),
            "n": r["n"],
            "spend": r["spend"] or 0,
            "leads": r["leads"] or 0,
        })

    daily = [{"day": r["day"], "spend": round(r["spend"] or 0, 2), "leads": r["leads"] or 0}
             for r in conn.execute("""
                 SELECT day, SUM(spend) spend, SUM(leads) leads
                 FROM daily_results GROUP BY day ORDER BY day
             """)]

    creatives = []
    for r in conn.execute("""
        SELECT c.creative_id, c.ad_name, c.campaign, c.headline, c.body, c.cta, c.angle,
               c.awareness_stage, c.first_seen, c.last_seen,
               a.optimization_goal, a.custom_event_type,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads,
               SUM(d.impressions) impressions, SUM(d.clicks) clicks
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        GROUP BY c.creative_id
        ORDER BY spend DESC
    """):
        ev = _event_label(r)
        spend, leads = r["spend"] or 0, r["leads"] or 0
        impressions = r["impressions"] or 0
        creatives.append({
            "id": r["creative_id"],
            "ad": r["ad_name"] or "(senza nome)",
            "campaign": r["campaign"] or "—",
            "headline": r["headline"] or "",
            "body": (r["body"] or "")[:220],
            "cta": r["cta"] or "",
            "angle": r["angle"],
            "awareness": r["awareness_stage"],
            "event": ev,
            "klass": EVENT_CLASSES.get(ev, "?"),
            "spend": spend,
            "leads": leads,
            "impressions": impressions,
            "clicks": r["clicks"] or 0,
            "ctr": round((r["clicks"] or 0) / impressions * 100, 2) if impressions else None,
            "cpl": round(spend / leads, 2) if leads else None,
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
        })

    accounts = [r["account_id"] for r in
                conn.execute("SELECT DISTINCT account_id FROM creatives WHERE account_id != ''")]
    conn.close()

    tagged = sum(1 for c in creatives if c["angle"])
    return {
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "range": [daily[0]["day"], daily[-1]["day"]] if daily else ["—", "—"],
        "accounts": accounts,
        "threshold": min_leads(),
        "class_note": CLASS_NOTE,
        "classes": classes,
        "daily": daily,
        "creatives": creatives,
        "tagged": tagged,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Dashboard HTML del Creative DB")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    a = p.parse_args()

    if not DB_PATH.exists():
        print(f"DB non trovato: {DB_PATH}\nLancia prima: python tools/creative_db.py import --days 90")
        return 1

    data = collect()
    if not data["creatives"]:
        print("DB vuoto — niente da mostrare.")
        return 1

    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(html, encoding="utf-8")

    print(f"Dashboard: {a.output}")
    print(f"  {len(data['creatives'])} creative · {len(data['daily'])} giorni · "
          f"{data['tagged']}/{len(data['creatives'])} classificate per angolo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
