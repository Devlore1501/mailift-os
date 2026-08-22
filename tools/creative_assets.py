#!/usr/bin/env python3
"""
Scarica in locale gli asset dei creative registrati nel Creative DB.

Perche' serve: gli URL fbcdn salvati in creatives.image_url sono firmati e
scadono (parametro `oe`), quindi dopo pochi giorni il DB contiene puntatori
morti. Qui salviamo i byte, non il link.

Limite noto: fetch_creative() in ads_creative_tracker.py usa image_url con
fallback su thumbnail_url senza distinguerli, quindi per gli ad video il file
scaricato e' un singolo fotogramma, non il video. Va bene per le statiche.

CLI:
  python tools/creative_assets.py download
  python tools/creative_assets.py download --force     # riscarica tutto
  python tools/creative_assets.py status
  python tools/creative_assets.py expiring             # URL vicini alla scadenza
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests

from creative_db import DB_PATH, connect, migrate

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "data" / "creative_assets"

ASSET_COLUMNS = {
    "asset_path": "TEXT",
    "asset_sha256": "TEXT",
    "asset_bytes": "INTEGER",
    "asset_type": "TEXT",
    "asset_downloaded_at": "TEXT",
    "asset_error": "TEXT",
}

EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
}


def migrate_assets(conn: sqlite3.Connection) -> None:
    migrate(conn)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(creatives)")}
    added = [c for c in ASSET_COLUMNS if c not in have]
    for col in added:
        conn.execute(f"ALTER TABLE creatives ADD COLUMN {col} {ASSET_COLUMNS[col]}")
    if added:
        conn.commit()
        print(f"  migrazione: aggiunte colonne {', '.join(added)}")


def url_expiry(url: str) -> datetime | None:
    """La scadenza sta nel parametro `oe`, in esadecimale."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "oe" not in q:
        return None
    try:
        return datetime.fromtimestamp(int(q["oe"][0], 16))
    except (ValueError, OverflowError, OSError):
        return None


def download_one(creative_id: str, url: str) -> dict:
    """Ritorna {path, sha256, bytes, type} oppure {error}."""
    exp = url_expiry(url)
    if exp and exp < datetime.now():
        return {"error": f"URL scaduto il {exp:%Y-%m-%d %H:%M}"}
    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException as e:
        return {"error": f"rete: {type(e).__name__}"}
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    if not r.content:
        return {"error": "risposta vuota"}

    ctype = r.headers.get("Content-Type", "").split(";")[0].strip()
    ext = EXT_BY_TYPE.get(ctype, ".bin")
    digest = hashlib.sha256(r.content).hexdigest()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    # Nome dal creative_id: stabile e ricollegabile al DB a colpo d'occhio.
    safe = creative_id.replace(":", "_").replace("/", "_")
    path = ASSETS_DIR / f"{safe}{ext}"
    path.write_bytes(r.content)

    return {"path": str(path.relative_to(ROOT)), "sha256": digest,
            "bytes": len(r.content), "type": ctype}


def download(force: bool) -> int:
    conn = connect()
    migrate_assets(conn)

    where = "image_url != ''" if force else "image_url != '' AND (asset_path IS NULL OR asset_path = '')"
    rows = conn.execute(f"SELECT creative_id, ad_name, image_url FROM creatives WHERE {where}").fetchall()

    if not rows:
        print("Niente da scaricare (usa --force per riscaricare tutto).")
        conn.close()
        return 0

    print(f"Scarico {len(rows)} asset in {ASSETS_DIR.relative_to(ROOT)}/")
    now = datetime.now().isoformat(timespec="seconds")
    ok = failed = 0

    for r in rows:
        res = download_one(r["creative_id"], r["image_url"])
        if "error" in res:
            failed += 1
            conn.execute("UPDATE creatives SET asset_error=?, asset_downloaded_at=? WHERE creative_id=?",
                         (res["error"], now, r["creative_id"]))
            print(f"  ✗ {(r['ad_name'] or '')[:44]:<46} {res['error']}")
        else:
            ok += 1
            conn.execute("""UPDATE creatives SET asset_path=?, asset_sha256=?, asset_bytes=?,
                            asset_type=?, asset_downloaded_at=?, asset_error=NULL
                            WHERE creative_id=?""",
                         (res["path"], res["sha256"], res["bytes"], res["type"], now, r["creative_id"]))
        conn.commit()

    conn.close()
    print(f"\n{ok} scaricati, {failed} falliti")
    return 0 if failed == 0 else 1


def status() -> int:
    conn = connect()
    migrate_assets(conn)
    tot = conn.execute("SELECT COUNT(*) c FROM creatives").fetchone()["c"]
    got = conn.execute("SELECT COUNT(*) c FROM creatives WHERE asset_path IS NOT NULL AND asset_path != ''").fetchone()["c"]
    err = conn.execute("SELECT COUNT(*) c FROM creatives WHERE asset_error IS NOT NULL").fetchone()["c"]
    size = conn.execute("SELECT COALESCE(SUM(asset_bytes),0) b FROM creatives").fetchone()["b"]

    print(f"Asset scaricati: {got}/{tot}  ({size/1e6:.1f} MB)")
    if err:
        print(f"Errori:          {err}")
        for r in conn.execute("""SELECT ad_name, asset_error FROM creatives
                                 WHERE asset_error IS NOT NULL LIMIT 10"""):
            print(f"  {(r['ad_name'] or '')[:44]:<46} {r['asset_error']}")

    # Stessa immagine riusata su piu' creative: utile prima di attribuire una
    # differenza di performance al visual.
    dupes = conn.execute("""
        SELECT asset_sha256, COUNT(*) n FROM creatives
        WHERE asset_sha256 IS NOT NULL GROUP BY asset_sha256 HAVING n > 1 ORDER BY n DESC
    """).fetchall()
    if dupes:
        uniq = conn.execute("SELECT COUNT(DISTINCT asset_sha256) c FROM creatives WHERE asset_sha256 IS NOT NULL").fetchone()["c"]
        print(f"\nImmagini uniche: {uniq} su {got} asset — {len(dupes)} riusate su piu' creative:")
        for d in dupes[:5]:
            names = [x["ad_name"] or "?" for x in conn.execute(
                "SELECT ad_name FROM creatives WHERE asset_sha256=? LIMIT 4", (d["asset_sha256"],))]
            print(f"  {d['n']}× {d['asset_sha256'][:10]} → {', '.join(n[:26] for n in names)}")
    conn.close()
    return 0


def expiring() -> int:
    conn = connect()
    migrate_assets(conn)
    rows = conn.execute("SELECT creative_id, ad_name, image_url, asset_path FROM creatives WHERE image_url != ''").fetchall()
    conn.close()

    now = datetime.now()
    dead = alive = noexp = 0
    soonest = None
    for r in rows:
        exp = url_expiry(r["image_url"])
        if exp is None:
            noexp += 1
        elif exp < now:
            dead += 1
        else:
            alive += 1
            soonest = exp if soonest is None or exp < soonest else soonest

    print(f"URL vivi: {alive} · scaduti: {dead} · senza scadenza: {noexp}")
    if soonest:
        h = (soonest - now).total_seconds() / 3600
        print(f"Prima scadenza: {soonest:%Y-%m-%d %H:%M} (fra {h:.0f}h)")
    saved = sum(1 for r in rows if r["asset_path"])
    print(f"Gia' salvati in locale: {saved}/{len(rows)} — questi sono al sicuro comunque.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Asset dei creative: scarica e verifica")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download", help="scarica gli asset mancanti")
    d.add_argument("--force", action="store_true", help="riscarica anche quelli gia' presenti")
    sub.add_parser("status", help="quanti asset, errori, duplicati")
    sub.add_parser("expiring", help="stato di scadenza degli URL")
    a = p.parse_args()

    if not DB_PATH.exists():
        print(f"DB non trovato: {DB_PATH}")
        return 1
    if a.cmd == "download":
        return download(a.force)
    if a.cmd == "status":
        return status()
    if a.cmd == "expiring":
        return expiring()
    return 0


if __name__ == "__main__":
    sys.exit(main())
