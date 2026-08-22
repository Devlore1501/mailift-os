#!/usr/bin/env python3
"""
Creative DB — registro persistente dei test creativi (copy, headline, angoli)
e dei loro risultati giornalieri.

Il DB e' la memoria di lungo periodo del loop ads: ads_creative_tracker.py
fotografa il presente, questo registra lo storico in modo che gli angoli
gia' testati non vengano ri-testati alla cieca.

Granularita' giornaliera (time_increment=1): le finestre di analisi
(3gg vs 7gg, ecc.) si ricalcolano a posteriori senza doppi conteggi.

CLI:
  python tools/creative_db.py init
  python tools/creative_db.py import --days 90
  python tools/creative_db.py import --days 90 --account act_2390793521074673
  python tools/creative_db.py list
  python tools/creative_db.py show <creative_id>
  python tools/creative_db.py tag <creative_id> --angle "secchio bucato" --awareness problem-aware
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from ads_creative_tracker import ACCOUNT as DEFAULT_ACCOUNT
from ads_creative_tracker import BASE, _paginate, cpl_from, fetch_creative, leads_from

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "creative_db.sqlite"

# Default: sotto questa soglia un confronto fra angoli e' rumore, non segnale.
# Il valore effettivo e' configurabile — usa min_leads() per leggerlo.
MIN_LEADS_FOR_VERDICT = 50


def min_leads() -> int:
    """Soglia effettiva da config, con fallback al default.
    Import locale: pipeline_config importa questo modulo."""
    try:
        from pipeline_config import get
        return get("min_leads_for_verdict")
    except Exception:
        return MIN_LEADS_FOR_VERDICT

SCHEMA = """
-- L'evento di ottimizzazione vive a livello adset, non creative: e' cio' che
-- rende confrontabili (o no) i CPL fra campagne con lo stesso objective Meta.
CREATE TABLE IF NOT EXISTS adsets (
    adset_id          TEXT PRIMARY KEY,
    account_id        TEXT,
    name              TEXT,
    campaign          TEXT,
    optimization_goal TEXT,
    custom_event_type TEXT,
    destination_type  TEXT,
    synced_at         TEXT
);

CREATE TABLE IF NOT EXISTS creatives (
    creative_id      TEXT PRIMARY KEY,
    account_id       TEXT NOT NULL,
    ad_id            TEXT,
    ad_name          TEXT,
    campaign         TEXT,
    adset            TEXT,
    adset_id         TEXT,
    headline         TEXT,
    body             TEXT,
    cta              TEXT,
    image_url        TEXT,
    -- Classificazione: popolata a mano o via AI, non dedotta da Meta.
    angle            TEXT,
    awareness_stage  TEXT,
    hook_type        TEXT,
    notes            TEXT,
    first_seen       TEXT,
    last_seen        TEXT,
    imported_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_results (
    creative_id  TEXT NOT NULL,
    ad_id        TEXT NOT NULL,
    day          TEXT NOT NULL,
    spend        REAL DEFAULT 0,
    impressions  INTEGER DEFAULT 0,
    clicks       INTEGER DEFAULT 0,
    ctr          REAL,
    cpm          REAL,
    leads        INTEGER DEFAULT 0,
    cpl          REAL,
    PRIMARY KEY (ad_id, day),
    FOREIGN KEY (creative_id) REFERENCES creatives(creative_id)
);

CREATE INDEX IF NOT EXISTS idx_daily_creative ON daily_results(creative_id);
CREATE INDEX IF NOT EXISTS idx_daily_day      ON daily_results(day);
CREATE INDEX IF NOT EXISTS idx_creatives_angle ON creatives(angle);
"""

# Creato dopo la migrazione: su un DB vecchio la colonna adset_id non esiste
# ancora quando gira SCHEMA, e l'indice fallirebbe.
SCHEMA_POST = """
CREATE INDEX IF NOT EXISTS idx_creatives_adset ON creatives(adset_id);
"""

# Meta riporta tutto sotto l'action_type "lead", ma sono cose diverse.
# Confrontare CPL fra classi diverse non ha senso; dentro una classe si'.
#   web      — conversione sul sito (funnel report.mailift.com)
#   leadform — modulo istantaneo dentro Meta, mai passato dal sito
#   junk     — evento custom che non e' un lead (gonfia i conteggi)
#   none     — non e' un evento lead
EVENT_CLASSES = {
    "LEAD":                  "web",
    # Optin del calcolatore su report.mailift.com: conversione sul sito, quindi
    # confrontabile con LEAD e non con i lead form di Meta.
    "COMPLETE_REGISTRATION": "web",
    "goal:QUALITY_LEAD":     "leadform",
    "goal:LEAD_GENERATION":  "leadform",
    "OTHER":                 "junk",
    "PURCHASE":              "none",
    "INITIATED_CHECKOUT":    "none",
}
CLASS_NOTE = {
    "web":      "lead dal sito — confrontabili fra loro",
    "leadform": "lead form Meta — confrontabili fra loro, NON con i lead web",
    "junk":     "⚠️ evento custom, NON sono lead: escludere dalle decisioni",
    "none":     "non e' un evento lead",
    "?":        "⚠️ non classificato — aggiungilo a EVENT_CLASSES",
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Il server di controllo e la CLI accedono allo stesso file insieme: senza
    # WAL un lettore blocca uno scrittore, e senza timeout la seconda scrittura
    # muore con "database is locked" invece di aspettare il suo turno.
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Aggiunge le colonne nuove ai DB creati da versioni precedenti."""
    conn.executescript(SCHEMA)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(creatives)")}
    if "adset_id" not in have:
        conn.execute("ALTER TABLE creatives ADD COLUMN adset_id TEXT")
        print("  migrazione: aggiunta colonna creatives.adset_id")
    conn.executescript(SCHEMA_POST)
    conn.commit()


def init_db() -> None:
    with connect() as conn:
        migrate(conn)
    print(f"DB pronto: {DB_PATH}")


# ── import da Meta ────────────────────────────────────────────────────────────

class RateLimited(RuntimeError):
    pass


def _guard(fn, *args, **kwargs):
    """Meta risponde 'User request limit reached' sotto carico: distinguiamo il
    throttling da un errore vero, cosi' un import parziale non sembra un bug."""
    try:
        return fn(*args, **kwargs)
    except RuntimeError as e:
        if "request limit" in str(e).lower():
            raise RateLimited(str(e)) from e
        raise


def fetch_daily_insights(account: str, since: str, until: str) -> list[dict]:
    """Insights a livello ad spezzati per giorno."""
    return _guard(_paginate, f"{BASE}/{account}/insights", {
        "level": "ad",
        "time_range": json.dumps({"since": since, "until": until}),
        "time_increment": 1,
        "fields": ("ad_id,ad_name,adset_id,adset_name,campaign_name,date_start,spend,"
                   "impressions,clicks,ctr,cpm,actions,cost_per_action_type"),
        "limit": 500,
    })


def sync_adsets(account: str, conn: sqlite3.Connection) -> int:
    """Scarica optimization_goal e custom_event_type per ogni adset."""
    now = datetime.now().isoformat(timespec="seconds")
    rows = _guard(_paginate, f"{BASE}/{account}/adsets", {
        "fields": "id,name,optimization_goal,destination_type,promoted_object,campaign{name}",
        "limit": 500,
    })
    for a in rows:
        po = a.get("promoted_object") or {}
        conn.execute("""
            INSERT INTO adsets (adset_id, account_id, name, campaign, optimization_goal,
                                custom_event_type, destination_type, synced_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(adset_id) DO UPDATE SET
                optimization_goal = excluded.optimization_goal,
                custom_event_type = excluded.custom_event_type,
                destination_type  = excluded.destination_type,
                synced_at         = excluded.synced_at
        """, (a["id"], account, a.get("name", ""), (a.get("campaign") or {}).get("name", ""),
              a.get("optimization_goal", ""), po.get("custom_event_type", ""),
              a.get("destination_type", ""), now))
    conn.commit()
    return len(rows)


def import_history(account: str, days: int) -> None:
    today = date.today()
    since = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    until = today.strftime("%Y-%m-%d")
    now = datetime.now().isoformat(timespec="seconds")

    print(f"Import {account}: {since} → {until}")
    rows = fetch_daily_insights(account, since, until)
    print(f"  {len(rows)} righe giornaliere da Meta")

    ads_raw = _paginate(f"{BASE}/{account}/ads", {"fields": "id,name,creative", "limit": 500})
    creative_by_ad = {a["id"]: a.get("creative", {}).get("id", "") for a in ads_raw}

    conn = connect()
    migrate(conn)

    n_adsets = sync_adsets(account, conn)
    print(f"  {n_adsets} adset sincronizzati (optimization_goal + evento)")

    # Il creative va scaricato una volta sola per id, non per riga giornaliera.
    creative_cache: dict[str, dict] = {}
    seen_days: dict[str, list[str]] = {}
    imported = 0

    for r in rows:
        ad_id = r["ad_id"]
        creative_id = creative_by_ad.get(ad_id) or f"unknown:{ad_id}"
        day = r["date_start"]
        seen_days.setdefault(creative_id, []).append(day)

        if creative_id not in creative_cache:
            if creative_id.startswith("unknown:"):
                creative_cache[creative_id] = {"headline": "", "body": "", "cta": "", "image_url": ""}
            else:
                creative_cache[creative_id] = fetch_creative(creative_id)

        c = creative_cache[creative_id]
        conn.execute("""
            INSERT INTO creatives (creative_id, account_id, ad_id, ad_name, campaign, adset,
                                   adset_id, headline, body, cta, image_url, imported_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(creative_id) DO UPDATE SET
                ad_name  = excluded.ad_name,
                campaign = excluded.campaign,
                adset    = excluded.adset,
                adset_id = excluded.adset_id
        """, (creative_id, account, ad_id, r.get("ad_name", ""), r.get("campaign_name", ""),
              r.get("adset_name", ""), r.get("adset_id", ""), c["headline"].strip(),
              c["body"].strip(), c["cta"], c["image_url"], now))

        leads = leads_from(r)
        cpl = cpl_from(r)
        conn.execute("""
            INSERT INTO daily_results (creative_id, ad_id, day, spend, impressions,
                                       clicks, ctr, cpm, leads, cpl)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(ad_id, day) DO UPDATE SET
                spend=excluded.spend, impressions=excluded.impressions,
                clicks=excluded.clicks, ctr=excluded.ctr, cpm=excluded.cpm,
                leads=excluded.leads, cpl=excluded.cpl
        """, (creative_id, ad_id, day, float(r.get("spend", 0)), int(r.get("impressions", 0)),
              int(r.get("clicks", 0)), float(r.get("ctr", 0) or 0), float(r.get("cpm", 0) or 0),
              leads, cpl))
        imported += 1

    for creative_id, days_list in seen_days.items():
        conn.execute("UPDATE creatives SET first_seen=?, last_seen=? WHERE creative_id=?",
                     (min(days_list), max(days_list), creative_id))

    conn.commit()
    creatives = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    conn.close()
    print(f"  {imported} risultati giornalieri, {creatives} creative in totale")


# ── query ─────────────────────────────────────────────────────────────────────

def _event_label(row: sqlite3.Row) -> str:
    """Come classificare i 'lead' di questo adset. Meta usa l'action_type 'lead'
    per eventi diversi: senza questa distinzione i CPL non sono confrontabili."""
    ev = row["custom_event_type"] or ""
    goal = row["optimization_goal"] or ""
    if ev:
        return ev
    if goal:
        return f"goal:{goal}"
    return "sconosciuto"


def list_creatives(event: str | None = None) -> None:
    conn = connect()
    migrate(conn)
    rows = conn.execute("""
        SELECT c.creative_id, c.ad_name, c.headline, c.angle,
               a.optimization_goal, a.custom_event_type,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        GROUP BY c.creative_id
        ORDER BY spend DESC
    """).fetchall()
    conn.close()

    if not rows:
        print("DB vuoto — lancia prima: python tools/creative_db.py import --days 90")
        return

    T = min_leads()
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(_event_label(r), []).append(r)

    for ev in sorted(groups, key=lambda e: -sum(g["spend"] or 0 for g in groups[e])):
        if event and ev != event:
            continue
        group = groups[ev]
        klass = EVENT_CLASSES.get(ev, "?")
        print(f"\n=== EVENTO: {ev}  [{klass}] ({len(group)} creative)")
        print(f"    {CLASS_NOTE[klass]}")
        print(f"{'AD':<32} {'ANGOLO':<16} {'SPESA':>8} {'LEAD':>5} {'CPL':>8}  VERDETTO")
        print("-" * 96)
        for r in group:
            leads = r["leads"] or 0
            cpl = f"€{r['spend']/leads:.2f}" if leads else "—"
            verdict = "ok" if leads >= T else f"rumore ({leads}/{T})"
            print(f"{(r['ad_name'] or '')[:31]:<32} {(r['angle'] or '—')[:15]:<16} "
                  f"€{r['spend'] or 0:>7.0f} {leads:>5} {cpl:>8}  {verdict}")
        g_spend = sum(r["spend"] or 0 for r in group)
        g_leads = sum(r["leads"] or 0 for r in group)
        ready = sum(1 for r in group if (r["leads"] or 0) >= T)
        print(f"→ €{g_spend:.0f} · {g_leads} lead · CPL medio "
              f"{'€%.2f' % (g_spend/g_leads) if g_leads else '—'} · "
              f"{ready} creative con dati sufficienti")


def show_events() -> None:
    """Breakdown per evento di ottimizzazione — la vista che dice quali CPL
    si possono confrontare fra loro."""
    conn = connect()
    migrate(conn)
    rows = conn.execute("""
        SELECT a.optimization_goal, a.custom_event_type,
               COUNT(DISTINCT c.creative_id) n,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        GROUP BY a.optimization_goal, a.custom_event_type
        ORDER BY spend DESC
    """).fetchall()
    conn.close()

    print(f"{'EVENTO':<20} {'OPT GOAL':<22} {'CLASSE':<10} {'CREATIVE':>8} {'SPESA':>8} {'LEAD':>6} {'CPL':>9}")
    print("-" * 96)
    for r in rows:
        ev = _event_label(r)
        leads = r["leads"] or 0
        spend = r["spend"] or 0
        cpl = f"€{spend/leads:.2f}" if leads else "—"
        klass = EVENT_CLASSES.get(ev, "?")
        print(f"{ev[:19]:<20} {(r['optimization_goal'] or '—')[:21]:<22} {klass:<10} {r['n']:>8} "
              f"€{spend:>7.0f} {leads:>6} {cpl:>9}")

    print()
    for klass in ("web", "leadform", "junk", "none", "?"):
        sel = [r for r in rows if EVENT_CLASSES.get(_event_label(r), "?") == klass]
        if not sel:
            continue
        spend = sum(r["spend"] or 0 for r in sel)
        leads = sum(r["leads"] or 0 for r in sel)
        cpl = f"€{spend/leads:.2f}" if leads else "—"
        print(f"{klass:<10} €{spend:>7.0f} · {leads:>4} lead · CPL {cpl:>8}   {CLASS_NOTE[klass]}")


def show_creative(creative_id: str) -> None:
    conn = connect()
    c = conn.execute("SELECT * FROM creatives WHERE creative_id=?", (creative_id,)).fetchone()
    if not c:
        print(f"Creative {creative_id} non trovato.")
        conn.close()
        return

    print(f"Creative:  {c['creative_id']}")
    print(f"Ad:        {c['ad_name']}  ({c['campaign']} / {c['adset']})")
    print(f"Headline:  {c['headline'] or '—'}")
    print(f"Body:      {(c['body'] or '—')[:200]}")
    print(f"CTA:       {c['cta'] or '—'}")
    print(f"Angolo:    {c['angle'] or '(non classificato)'}")
    print(f"Awareness: {c['awareness_stage'] or '(non classificato)'}")
    print(f"Hook:      {c['hook_type'] or '(non classificato)'}")
    print(f"Attivo:    {c['first_seen']} → {c['last_seen']}")

    days = conn.execute("""
        SELECT day, spend, impressions, clicks, ctr, cpm, leads
        FROM daily_results WHERE creative_id=? ORDER BY day
    """, (creative_id,)).fetchall()
    conn.close()

    print(f"\n{'GIORNO':<12} {'SPESA':>8} {'IMPR':>8} {'CTR':>7} {'CPM':>8} {'LEAD':>5}")
    for d in days:
        print(f"{d['day']:<12} €{d['spend']:>7.2f} {d['impressions']:>8} "
              f"{d['ctr'] or 0:>6.2f}% €{d['cpm'] or 0:>7.2f} {d['leads']:>5}")

    tot_spend = sum(d["spend"] for d in days)
    tot_leads = sum(d["leads"] for d in days)
    print(f"\nTotale: €{tot_spend:.2f} · {tot_leads} lead · "
          f"CPL {'€%.2f' % (tot_spend/tot_leads) if tot_leads else '—'}")
    T = min_leads()
    if tot_leads < T:
        print(f"⚠️  {tot_leads} lead: sotto la soglia di {T}, "
              f"il CPL qui non e' un segnale affidabile.")


def tag_creative(creative_id: str, angle: str | None, awareness: str | None,
                 hook: str | None, notes: str | None) -> None:
    fields = {"angle": angle, "awareness_stage": awareness, "hook_type": hook, "notes": notes}
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        print("Nessun campo da aggiornare.")
        return

    conn = connect()
    sets = ", ".join(f"{k}=?" for k in updates)
    cur = conn.execute(f"UPDATE creatives SET {sets} WHERE creative_id=?",
                       (*updates.values(), creative_id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        print(f"Creative {creative_id} non trovato.")
    else:
        print(f"{creative_id} aggiornato: {', '.join(f'{k}={v!r}' for k, v in updates.items())}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Creative DB — registro test creativi ads")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="crea lo schema")

    imp = sub.add_parser("import", help="importa storico da Meta")
    imp.add_argument("--days", type=int, default=90)
    imp.add_argument("--account", default=DEFAULT_ACCOUNT,
                     help=f"ad account (default da .env: {DEFAULT_ACCOUNT or 'non impostato'})")

    lst = sub.add_parser("list", help="elenca creative raggruppate per evento")
    lst.add_argument("--event", help="filtra su un solo evento (es. LEAD)")

    sub.add_parser("events", help="breakdown per evento di ottimizzazione")

    sync = sub.add_parser("sync-adsets", help="aggiorna solo optimization_goal/evento")
    sync.add_argument("--account", default=DEFAULT_ACCOUNT)

    show = sub.add_parser("show", help="dettaglio di un creative")
    show.add_argument("creative_id")

    tag = sub.add_parser("tag", help="classifica un creative")
    tag.add_argument("creative_id")
    tag.add_argument("--angle")
    tag.add_argument("--awareness")
    tag.add_argument("--hook")
    tag.add_argument("--notes")

    a = p.parse_args()

    try:
        if a.cmd == "init":
            init_db()
        elif a.cmd == "import":
            if not a.account:
                print("Nessun account: passa --account act_XXX o imposta FB_AD_ACCOUNT_ID nel .env")
                return 1
            import_history(a.account, a.days)
        elif a.cmd == "sync-adsets":
            conn = connect()
            migrate(conn)
            n = sync_adsets(a.account, conn)
            conn.close()
            print(f"{n} adset sincronizzati")
        elif a.cmd == "events":
            show_events()
        elif a.cmd == "list":
            list_creatives(a.event)
        elif a.cmd == "show":
            show_creative(a.creative_id)
        elif a.cmd == "tag":
            tag_creative(a.creative_id, a.angle, a.awareness, a.hook, a.notes)
    except RateLimited as e:
        print(f"\n⛔ Meta rate limit: {e}")
        print("   Non e' un errore del tool. Aspetta ~1h e rilancia: i dati gia'")
        print("   importati restano, l'import e' idempotente (UPSERT su ad_id+giorno).")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
