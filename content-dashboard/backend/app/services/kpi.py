"""Aggregazioni KPI (M2): overview, mix pillar, breakdown per format/pillar/surface,
winner detection e kill flag. Le soglie vengono dalle Impostazioni (tabella settings).

Il dataset atteso è di centinaia di contenuti (NFR-01): le aggregazioni sono fatte
in Python sull'ultimo snapshot metrico di ogni contenuto.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from ..enums import DEFAULT_PILLAR_TARGETS, DEFAULT_SETTINGS, FORMATS, PILLARS, SURFACES
from ..models import Content, Metric, PillarTarget, Setting, utcnow
from ..util import naive_utc


def get_settings_map(db: Session) -> dict:
    values = dict(DEFAULT_SETTINGS)
    for row in db.query(Setting).all():
        values[row.key] = row.value
    return values


def setting_float(settings: dict, key: str) -> float:
    return float(settings.get(key, DEFAULT_SETTINGS[key]))


def latest_metric(content: Content) -> Metric | None:
    if not content.metrics:
        return None
    return max(content.metrics, key=lambda m: (m.captured_at or datetime.min, m.id))


def _published_contents(db: Session, date_from=None, date_to=None, platform=None) -> list[Content]:
    q = (
        db.query(Content)
        .options(joinedload(Content.metrics))
        .filter(Content.status.in_(["published", "archived"]))
        .filter(Content.published_at.isnot(None))
    )
    if date_from:
        q = q.filter(Content.published_at >= naive_utc(date_from))
    if date_to:
        q = q.filter(Content.published_at <= naive_utc(date_to))
    if platform:
        q = q.filter(Content.platform == platform)
    return q.all()


def _avg(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def _percentile(values: list[float], pct: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    idx = max(0, min(len(vals) - 1, round(pct / 100 * (len(vals) - 1))))
    return vals[idx]


def compute_winner_ids(contents: list[Content], settings: dict) -> set[int]:
    """Winner rule (default, editabile): retention media > soglia OPPURE save rate top-decile."""
    retention_min = setting_float(settings, "winner_retention_pct")
    decile = setting_float(settings, "winner_save_rate_decile")
    pairs = [(c, latest_metric(c)) for c in contents]
    save_rates = [m.save_rate for _, m in pairs if m and m.save_rate is not None]
    save_cut = _percentile(save_rates, decile)
    winners = set()
    for c, m in pairs:
        if not m:
            continue
        if m.avg_retention_pct is not None and m.avg_retention_pct > retention_min:
            winners.add(c.id)
        elif save_cut is not None and m.save_rate is not None and m.save_rate >= save_cut and len(save_rates) >= 3:
            winners.add(c.id)
    return winners


def _aggregate(pairs: list[tuple[Content, Metric | None]]) -> dict:
    metrics = [m for _, m in pairs if m]
    icp = sum(m.icp_comments or 0 for m in metrics)
    non_icp = sum(m.non_icp_comments or 0 for m in metrics)
    triggers = sum(m.dm_keyword_triggers or 0 for m in metrics)
    purchases = sum(m.fhs_purchases or 0 for m in metrics)
    return {
        "n_posts": len(pairs),
        "n_with_metrics": len(metrics),
        "avg_retention_pct": _avg([m.avg_retention_pct for m in metrics]),
        "hook_retention_pct": _avg([m.hook_retention_pct for m in metrics]),
        "rewatch_rate": _avg([m.rewatch_rate for m in metrics]),
        "save_rate": _avg([m.save_rate for m in metrics]),
        "share_rate": _avg([m.share_rate for m in metrics]),
        "icp_ratio": round(icp / (icp + non_icp), 4) if (icp + non_icp) > 0 else None,
        "dm_keyword_triggers": triggers,
        "fhs_clicks": sum(m.fhs_clicks or 0 for m in metrics),
        "fhs_purchases": purchases,
        "dm_fhs_rate": round(purchases / triggers, 4) if triggers > 0 else None,
        # vanity — sezione secondaria (principio Qualità > vanity)
        "views": sum(m.views or 0 for m in metrics),
        "likes": sum(m.likes or 0 for m in metrics),
    }


def overview(db: Session, date_from=None, date_to=None, platform=None) -> dict:
    settings = get_settings_map(db)
    contents = _published_contents(db, date_from, date_to, platform)
    pairs = [(c, latest_metric(c)) for c in contents]
    agg = _aggregate(pairs)
    winners = compute_winner_ids(contents, settings)

    # Contenuti pubblicati da più di N ore senza metriche (metrica di adozione §3)
    reminder_hours = setting_float(settings, "metrics_reminder_hours")
    cutoff = utcnow() - timedelta(hours=reminder_hours)
    missing_metrics = [
        {"id": c.id, "title": c.title or (c.idea.title if c.idea else f"Contenuto #{c.id}"),
         "published_at": c.published_at.isoformat() if c.published_at else None}
        for c, m in pairs
        if m is None and c.published_at and naive_utc(c.published_at) < cutoff
    ]

    return {
        "primary": {k: agg[k] for k in (
            "avg_retention_pct", "hook_retention_pct", "rewatch_rate", "save_rate",
            "share_rate", "icp_ratio", "dm_fhs_rate", "dm_keyword_triggers",
            "fhs_clicks", "fhs_purchases",
        )},
        "secondary": {"views": agg["views"], "likes": agg["likes"]},
        "n_published": agg["n_posts"],
        "n_with_metrics": agg["n_with_metrics"],
        "winner_ids": sorted(winners),
        "missing_metrics": missing_metrics,
        "trend": _weekly_trend(pairs),
    }


def _weekly_trend(pairs) -> list[dict]:
    """Serie storica per settimana ISO di pubblicazione (FR-M2-05)."""
    buckets: dict[str, list] = {}
    for c, m in pairs:
        if not c.published_at:
            continue
        year, week, _ = c.published_at.isocalendar()
        key = f"{year}-W{week:02d}"
        buckets.setdefault(key, []).append((c, m))
    out = []
    for key in sorted(buckets):
        agg = _aggregate(buckets[key])
        out.append({
            "week": key,
            "n_posts": agg["n_posts"],
            "avg_retention_pct": agg["avg_retention_pct"],
            "hook_retention_pct": agg["hook_retention_pct"],
            "save_rate": agg["save_rate"],
            "share_rate": agg["share_rate"],
            "icp_ratio": agg["icp_ratio"],
            "views": agg["views"],
        })
    return out


def pillar_mix(db: Session, date_from=None, date_to=None) -> dict:
    """Mix pillar reale vs target con alert oltre soglia (FR-M1-08).

    Conta i contenuti attivi (non archiviati) datati per publish/schedule/creazione.
    """
    settings = get_settings_map(db)
    alert_pp = setting_float(settings, "pillar_mix_alert_pp")

    targets = {row.pillar: row.target_pct for row in db.query(PillarTarget).all()}
    if not targets:
        targets = {k: float(v) for k, v in DEFAULT_PILLAR_TARGETS.items()}

    date_from, date_to = naive_utc(date_from), naive_utc(date_to)
    q = db.query(Content).filter(Content.status != "archived")
    contents = []
    for c in q.all():
        ref_date = naive_utc(c.published_at or c.scheduled_at or c.created_at)
        if date_from and ref_date and ref_date < date_from:
            continue
        if date_to and ref_date and ref_date > date_to:
            continue
        contents.append(c)

    total = len(contents)
    counts: dict[str, int] = {p: 0 for p in PILLARS}
    for c in contents:
        pillar = c.pillar or (c.idea.pillar if c.idea else None)
        if pillar in counts:
            counts[pillar] += 1

    rows, alerts = [], []
    for pillar in PILLARS:
        real_pct = round(100 * counts[pillar] / total, 1) if total else 0.0
        target_pct = targets.get(pillar, 0.0)
        delta = round(real_pct - target_pct, 1)
        row = {
            "pillar": pillar, "label": PILLARS[pillar], "count": counts[pillar],
            "real_pct": real_pct, "target_pct": target_pct, "delta_pp": delta,
            "alert": total > 0 and abs(delta) > alert_pp,
        }
        rows.append(row)
        if row["alert"]:
            alerts.append(
                f"{PILLARS[pillar]} al {real_pct:g}% vs {target_pct:g}% target ({delta:+g} pp)"
            )
    return {"total": total, "rows": rows, "alerts": alerts, "alert_threshold_pp": alert_pp}


def breakdown(db: Session, by: str, date_from=None, date_to=None, platform=None) -> dict:
    """KPI aggregati per format (FR-M2-06), pillar o surface (FR-M2-07),
    con winner count, kill flag (FR-M2-09) e flag campione insufficiente."""
    assert by in ("format", "pillar", "surface")
    settings = get_settings_map(db)
    contents = _published_contents(db, date_from, date_to, platform)
    winners = compute_winner_ids(contents, settings)

    kill_retention = setting_float(settings, "kill_retention_pct")
    kill_min = int(setting_float(settings, "kill_min_posts"))
    sample_min = int(setting_float(settings, "format_min_posts"))
    labels = {"format": FORMATS, "pillar": PILLARS, "surface": SURFACES}[by]

    groups: dict[str, list] = {}
    for c in contents:
        key = getattr(c, by) or (c.idea.pillar if by == "pillar" and c.idea else None)
        groups.setdefault(key or "_none", []).append(c)

    rows = []
    for key, group in groups.items():
        pairs = [(c, latest_metric(c)) for c in group]
        agg = _aggregate(pairs)
        retention = agg["avg_retention_pct"]
        kill = (
            by == "format"
            and agg["n_with_metrics"] >= kill_min
            and retention is not None
            and retention < kill_retention
        )
        rows.append({
            "key": key,
            "label": labels.get(key, "Senza " + by),
            **agg,
            "winner_count": sum(1 for c in group if c.id in winners),
            "kill_flag": kill,
            "insufficient_sample": agg["n_with_metrics"] < sample_min,
            "content_ids": [c.id for c in group],
        })
    rows.sort(key=lambda r: (r["avg_retention_pct"] is None, -(r["avg_retention_pct"] or 0)))
    return {
        "by": by,
        "rows": rows,
        "thresholds": {
            "kill_retention_pct": kill_retention,
            "kill_min_posts": kill_min,
            "format_min_posts": sample_min,
            "winner_retention_pct": setting_float(settings, "winner_retention_pct"),
        },
    }
