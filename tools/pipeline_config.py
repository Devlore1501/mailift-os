#!/usr/bin/env python3
"""
Configurazione e stato della pipeline creative, persistiti nel Creative DB.

Tre tabelle:
  config   — chiave/valore tipizzato, con default dichiarati qui
  runs     — storico esecuzioni degli stage (esito, durata, errore)
  variants — proposte di varianti generate, con approvazione umana

CLI:
  python tools/pipeline_config.py show
  python tools/pipeline_config.py set min_leads_for_verdict 30
  python tools/pipeline_config.py reset min_leads_for_verdict
  python tools/pipeline_config.py runs
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime

from creative_db import connect, migrate

SCHEMA = """
CREATE TABLE IF NOT EXISTS config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL,          -- running | ok | error | skipped
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    duration_s  REAL,
    summary     TEXT,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_stage ON runs(stage, started_at);

CREATE TABLE IF NOT EXISTS variants (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_creative_id TEXT,
    angle              TEXT,
    awareness_stage    TEXT,
    hook_type          TEXT,
    headline           TEXT,
    body               TEXT,
    cta                TEXT,
    rationale          TEXT,
    asset_path         TEXT,
    source             TEXT,            -- manus | manuale
    manus_task_id      TEXT,
    status             TEXT NOT NULL DEFAULT 'proposed',  -- proposed|approved|rejected|published
    created_at         TEXT NOT NULL,
    decided_at         TEXT,
    decided_note       TEXT,
    FOREIGN KEY (parent_creative_id) REFERENCES creatives(creative_id)
);
CREATE INDEX IF NOT EXISTS idx_variants_status ON variants(status);
"""

# (default, tipo, descrizione) — la descrizione finisce nella dashboard.
DEFAULTS: dict[str, tuple] = {
    "min_leads_for_verdict": (50, int,
        "Lead minimi perché il CPL di un creative sia un segnale e non rumore."),
    "import_days": (90, int,
        "Giorni di storico da importare da Meta a ogni run."),
    "accounts": (["act_1495124847595184", "act_2390793521074673"], list,
        "Ad account Meta da importare."),
    "fatigue_days_recent": (3, int,
        "Giorni della finestra recente nel confronto fatigue."),
    "fatigue_days_baseline": (7, int,
        "Giorni della finestra di riferimento nel confronto fatigue."),
    "fatigue_freq_threshold": (2.0, float,
        "Frequenza oltre la quale un creative è considerato saturo."),
    "fatigue_min_spend": (20.0, float,
        "Spesa minima perché valga la pena valutare la fatigue di un creative."),
    "variants_per_run": (5, int,
        "Quante varianti chiedere a Manus per ogni generazione."),
    "generation_gate": (True, bool,
        "Se attivo, blocca la generazione su angoli senza dati sufficienti. "
        "Disattivarlo significa generare varianti basate su rumore statistico."),
    "auto_publish": (False, bool,
        "Pubblicazione automatica su Meta. Tenuto a False di proposito: le ads "
        "sono comunicazione esterna con budget reale e vogliono un OK umano."),
    "classifier_model": ("claude-opus-4-8", str,
        "Modello usato per classificare angolo/awareness/hook."),
    "image_model": ("gpt-image-2", str,
        "Modello di generazione immagini che Manus deve usare per le varianti."),
    "manus_ad_skill": ("mailift-ad-creator", str,
        "Skill Manus forzata sulla conversazione creative."),
    "manus_session_task_id": ("", str,
        "Conversazione Manus riusata per tutte le richieste. Vuoto = ne apre una "
        "nuova alla prossima richiesta. Riusarla tiene caldo il contesto."),
    "images_per_batch": (5, int,
        "Quante immagini chiedere a Manus in un solo messaggio, invece di una per task."),
    "manus_poll_timeout_s": (900, int,
        "Secondi massimi di attesa per un task Manus prima di considerarlo fallito."),
}


def ensure(conn: sqlite3.Connection) -> None:
    migrate(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def _decode(key: str, raw: str):
    _, typ, _ = DEFAULTS[key]
    if typ is bool:
        return raw == "1"
    if typ is list:
        return json.loads(raw)
    return typ(raw)


def _encode(key: str, val) -> str:
    _, typ, _ = DEFAULTS[key]
    if typ is bool:
        if isinstance(val, str):
            val = val.strip().lower() in ("1", "true", "si", "sì", "yes", "on")
        return "1" if val else "0"
    if typ is list:
        return json.dumps(val if isinstance(val, list) else json.loads(val))
    return str(typ(val))


def get(key: str, conn: sqlite3.Connection | None = None):
    if key not in DEFAULTS:
        raise KeyError(f"chiave di config sconosciuta: {key}")
    own = conn is None
    conn = conn or connect()
    ensure(conn)
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    if own:
        conn.close()
    return _decode(key, row["value"]) if row else DEFAULTS[key][0]


def set_(key: str, value, conn: sqlite3.Connection | None = None) -> None:
    if key not in DEFAULTS:
        raise KeyError(f"chiave di config sconosciuta: {key}")
    own = conn is None
    conn = conn or connect()
    ensure(conn)
    conn.execute("""INSERT INTO config (key, value, updated_at) VALUES (?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                                                   updated_at=excluded.updated_at""",
                 (key, _encode(key, value), datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    if own:
        conn.close()


def reset(key: str, conn: sqlite3.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    ensure(conn)
    conn.execute("DELETE FROM config WHERE key=?", (key,))
    conn.commit()
    if own:
        conn.close()


def all_config(conn: sqlite3.Connection | None = None) -> list[dict]:
    own = conn is None
    conn = conn or connect()
    ensure(conn)
    overrides = {r["key"]: r for r in conn.execute("SELECT key, value, updated_at FROM config")}
    out = []
    for key, (default, typ, desc) in DEFAULTS.items():
        o = overrides.get(key)
        out.append({
            "key": key,
            "value": _decode(key, o["value"]) if o else default,
            "default": default,
            "type": typ.__name__,
            "desc": desc,
            "overridden": o is not None,
            "updated_at": o["updated_at"] if o else None,
        })
    if own:
        conn.close()
    return out


# ── runs ──────────────────────────────────────────────────────────────────────

def start_run(stage: str, conn: sqlite3.Connection) -> int:
    ensure(conn)
    cur = conn.execute("INSERT INTO runs (stage, status, started_at) VALUES (?,?,?)",
                       (stage, "running", datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return cur.lastrowid


def finish_run(run_id: int, conn: sqlite3.Connection, status: str,
               summary: str = "", error: str = "") -> None:
    row = conn.execute("SELECT started_at FROM runs WHERE id=?", (run_id,)).fetchone()
    started = datetime.fromisoformat(row["started_at"])
    now = datetime.now()
    conn.execute("""UPDATE runs SET status=?, finished_at=?, duration_s=?, summary=?, error=?
                    WHERE id=?""",
                 (status, now.isoformat(timespec="seconds"),
                  round((now - started).total_seconds(), 1), summary, error or None, run_id))
    conn.commit()


def reconcile_runs(conn: sqlite3.Connection) -> int:
    """Chiude i run rimasti 'running' da un processo morto.

    Uno stage gira in-process: se questo processo sta partendo adesso, nessun
    run precedente può essere ancora vivo. Senza questo, un crash lascia una
    riga 'running' per sempre e lo stato mostra un lavoro che non esiste.
    """
    ensure(conn)
    cur = conn.execute(
        """UPDATE runs SET status='interrupted', finished_at=?,
           error='processo terminato prima della fine dello stage'
           WHERE status='running'""",
        (datetime.now().isoformat(timespec="seconds"),))
    conn.commit()
    return cur.rowcount


def recent_runs(limit: int = 25, conn: sqlite3.Connection | None = None) -> list[dict]:
    own = conn is None
    conn = conn or connect()
    ensure(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))]
    if own:
        conn.close()
    return rows


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="Config della pipeline creative")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    s = sub.add_parser("set"); s.add_argument("key"); s.add_argument("value")
    r = sub.add_parser("reset"); r.add_argument("key")
    sub.add_parser("runs")
    a = p.parse_args()

    if a.cmd == "show":
        for c in all_config():
            mark = "*" if c["overridden"] else " "
            print(f"{mark} {c['key']:<24} {str(c['value']):<42} (default {c['default']})")
        print("\n* = modificato rispetto al default")
    elif a.cmd == "set":
        try:
            set_(a.key, a.value)
        except KeyError as e:
            print(e); return 1
        print(f"{a.key} = {get(a.key)}")
    elif a.cmd == "reset":
        try:
            reset(a.key)
        except KeyError as e:
            print(e); return 1
        print(f"{a.key} = {get(a.key)} (default)")
    elif a.cmd == "runs":
        rows = recent_runs()
        if not rows:
            print("Nessun run registrato.")
            return 0
        print(f"{'ID':>4} {'STAGE':<12} {'ESITO':<9} {'DURATA':>8}  QUANDO             RIEPILOGO")
        for r in rows:
            d = f"{r['duration_s']:.1f}s" if r["duration_s"] is not None else "—"
            print(f"{r['id']:>4} {r['stage']:<12} {r['status']:<9} {d:>8}  "
                  f"{r['started_at']}  {(r['summary'] or r['error'] or '')[:46]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
