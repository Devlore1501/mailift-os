#!/usr/bin/env python3
"""
Genera l'immagine di ogni variante passando da Manus (skill mailift-ad-creator),
che a sua volta usa GPT Image 2.

Perché via Manus e non chiamando OpenAI direttamente: la skill `mailift-ad-creator`
sull'account Manus contiene già le regole visive di Mailift. Rifarle in un prompt
qui significherebbe tenerle allineate a mano in due posti.

Perché allegare la creative di riferimento: lo stile non è uno solo. L'angolo
klaviyo-mal-usato gira su fondo nero con verde acido, anti-newsletter su fondo
chiaro disegnato a mano. Ereditare lo stile dal riferimento che ha prodotto lead
è più affidabile che descriverlo a parole.

CLI:
  python tools/variant_images.py render            # tutte le varianti senza immagine
  python tools/variant_images.py render --id 3
  python tools/variant_images.py render --status approved
  python tools/variant_images.py render --dry-run  # stampa il prompt, non chiama
  python tools/variant_images.py status
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests

from creative_db import connect
from manus_bridge import _client, _upload
from pipeline_config import ensure, get

ROOT = Path(__file__).resolve().parent.parent
VARIANT_DIR = ROOT / "data" / "variant_assets"

RENDER_COLUMNS = {
    "rendered_at": "TEXT",
    "render_error": "TEXT",
    "render_task_id": "TEXT",
    "image_model": "TEXT",
}


def migrate_images(conn: sqlite3.Connection) -> None:
    ensure(conn)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(variants)")}
    added = [c for c in RENDER_COLUMNS if c not in have]
    for col in added:
        conn.execute(f"ALTER TABLE variants ADD COLUMN {col} {RENDER_COLUMNS[col]}")
    if added:
        conn.commit()
        print(f"  migrazione: aggiunte colonne variants.{', '.join(added)}")


def reference_asset(conn, variant: sqlite3.Row) -> Path | None:
    if not variant["parent_creative_id"]:
        return None
    row = conn.execute("SELECT asset_path FROM creatives WHERE creative_id=?",
                       (variant["parent_creative_id"],)).fetchone()
    if not row or not row["asset_path"]:
        return None
    p = ROOT / row["asset_path"]
    return p if p.exists() else None


def _variant_block(variant: sqlite3.Row, n: int) -> str:
    extra = json.loads(variant["rationale"] or "{}")
    brief = extra.get("visual_brief") or "Nessun brief visivo: deducilo dal copy."
    fam = (variant["format_family"] if "format_family" in variant.keys() else None) or "statica"
    # Il claim va passato INTERO: il modello renderizza fedelmente quello che
    # riceve, quindi troncare a metà frase produce un annuncio con la frase
    # tagliata stampata sopra.
    return f"""IMMAGINE {n} — nome file: variante_{variant['id']}.png  (famiglia: {fam})
  Headline:  {variant['headline']}
  Claim:     {(variant['body'] or '').strip()}
  Pulsante:  {variant['cta'] or 'Scopri di più'}
  Visual:    {brief}"""


def build_batch_prompt(variants: list[sqlite3.Row], model: str, has_ref: bool) -> str:
    """Un solo messaggio per N immagini: N task separati ripagherebbero N volte
    il caricamento della skill e del contesto, per lo stesso risultato."""
    ref_line = (
        "In allegato la creative di riferimento: è un annuncio REALE che ha prodotto "
        "lead. Eredita da quella lo stile visivo — palette, trattamento tipografico, "
        "tono dell'illustrazione, impaginazione. Le nuove devono sembrare della stessa "
        "famiglia visiva, pur essendo entità diverse per messaggio/formato."
        if has_ref else
        "Nessuna creative di riferimento allegata: usa lo stile Mailift della skill."
    )
    blocks = "\n\n".join(_variant_block(v, i + 1) for i, v in enumerate(variants))

    return f"""Genera {len(variants)} immagini per annunci Facebook Mailift, quadrate 1:1.
Usa il modello **{model}**. Consegnale TUTTE E {len(variants)} come allegati in questa
conversazione, una per ogni blocco qui sotto.

{ref_line}

{blocks}

REGOLE PER TUTTE
- Il testo va renderizzato in italiano ESATTAMENTE come scritto sopra: nessuna
  parola storpiata, nessun carattere inventato, niente riscritture creative.
- Headline in alto, un solo elemento visivo chiaro al centro, CTA come pulsante in basso.
  Meno immagine, più headline: il caos abbassa lo stopping power e la credibilità.
- Niente watermark, loghi di terzi, volti riconoscibili.
- Niente dashboard o numeri inventati: usa solo le cifre presenti nei testi sopra.
- Non renderizzare due immagini quasi identiche fra loro.

Allega le {len(variants)} immagini finali. Se una non riesce, allega comunque le altre
e dimmi quale manca."""


async def _render_batch(prompt: str, ref: Path | None, skill: str, timeout_s: int,
                        want: int) -> tuple[str, list]:
    """Manda UN messaggio nella conversazione condivisa e attende `want` immagini."""
    from manus_mcp.schemas.tasks import FilePart, TextPart

    from manus_bridge import session_kickoff
    from manus_session import ensure_session, send_and_wait

    client = _client()
    try:
        task_id, _ = await ensure_session(client, skill, session_kickoff(skill))
        parts = [TextPart(type="text", text=prompt)]
        if ref:
            parts.append(FilePart(type="file", file_id=await _upload(client, ref)))
        _text, attachments = await send_and_wait(client, task_id, parts, timeout_s,
                                                 want_images=want)
        return task_id, attachments
    finally:
        await client.aclose()


def _pick_image(attachments: list):
    for a in attachments:
        ctype = (a.content_type or "").lower()
        name = (a.filename or "").lower()
        if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            return a
    return None


def _match(variants: list[sqlite3.Row], images: list) -> dict[int, object]:
    """Abbina immagine → variante dal nome file (`variante_<id>.png`).

    Il nome è la richiesta esplicita nel prompt. Se Manus non lo rispetta si
    ripiega sull'ordine, ma solo quando i conti tornano: assegnare a caso
    significherebbe attaccare il copy sbagliato all'immagine sbagliata.
    """
    out: dict[int, object] = {}
    left = list(images)
    for v in variants:
        # \b sull'id: "variante_1" è dentro "variante_10.png", e un match
        # approssimativo attaccherebbe il copy della 1 all'immagine della 10.
        pat = re.compile(rf"variante_{v['id']}\b")
        for img in list(left):
            if pat.search((getattr(img, "filename", "") or "").lower()):
                out[v["id"]] = img
                left.remove(img)
                break
    unmatched = [v for v in variants if v["id"] not in out]
    if unmatched and len(left) == len(unmatched):
        for v, img in zip(unmatched, left):
            out[v["id"]] = img
    return out


def save_image(conn, vid: int, task_id: str, attachments: list, model: str) -> str:
    img = _pick_image(attachments)
    if not img or not img.url:
        raise RuntimeError(f"il task {task_id} non ha restituito un'immagine "
                           f"({len(attachments)} allegati)")

    r = requests.get(img.url, timeout=60)
    if r.status_code != 200 or not r.content:
        raise RuntimeError(f"download allegato fallito: HTTP {r.status_code}")

    VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(img.filename or "x.png").suffix or ".png"
    path = VARIANT_DIR / f"variant_{vid}{ext}"
    path.write_bytes(r.content)

    conn.execute("""UPDATE variants SET asset_path=?, rendered_at=?, render_task_id=?,
                    image_model=?, render_error=NULL WHERE id=?""",
                 (str(path.relative_to(ROOT)), datetime.now().isoformat(timespec="seconds"),
                  task_id, model, vid))
    conn.commit()
    return str(path.relative_to(ROOT))


async def _recover_image(task_id: str) -> list:
    """Tutti gli allegati di un task, senza attendere: serve dopo un timeout."""
    from manus_session import _message_ids, _new_assistant
    client = _client()
    try:
        _text, attachments = await _new_assistant(client, task_id, set())
        return attachments
    finally:
        await client.aclose()


def recover(task_id: str, vid: int) -> int:
    """Salva l'immagine di un task Manus già eseguito (es. dopo un timeout)."""
    conn = connect()
    migrate_images(conn)
    model = get("image_model", conn)
    try:
        attachments = asyncio.run(_recover_image(task_id))
        out = save_image(conn, vid, task_id, attachments, model)
    except Exception as e:
        print(f"✗ {type(e).__name__}: {e}")
        conn.close()
        return 1
    conn.close()
    print(f"✓ immagine della variante {vid} recuperata dal task {task_id}: {out}")
    return 0


def render(vid: int | None, status: str | None, force: bool, dry_run: bool,
           quiet: bool = False) -> tuple[int, int]:
    """Ritorna (fatte, fallite)."""
    conn = connect()
    migrate_images(conn)
    model = get("image_model", conn)
    skill = get("manus_ad_skill", conn)
    timeout_s = get("manus_poll_timeout_s", conn)

    where = ["1=1"]
    args: list = []
    if vid:
        where.append("id=?")
        args.append(vid)
    else:
        # Le rifiutate non si renderizzano: sarebbe pagare per un'immagine scartata.
        where.append("status IN ('proposed','approved')" if not status else "status=?")
        if status:
            args.append(status)
        if not force:
            where.append("(asset_path IS NULL OR asset_path = '')")

    rows = conn.execute(f"SELECT * FROM variants WHERE {' AND '.join(where)} ORDER BY id",
                        args).fetchall()
    # I formati che vanno girati o registrati non si generano: una dashboard
    # Klaviyo finta vale meno di zero. Restano nel DB come brief di produzione.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(variants)")}
    if "da_produrre" in cols:
        skipped = [v for v in rows if v["da_produrre"]]
        rows = [v for v in rows if not v["da_produrre"]]
        if skipped and not quiet:
            print(f"  ({len(skipped)} da produrre, non generabili con l'AI: "
                  f"{', '.join(str(v['id']) for v in skipped)})")
    if not rows:
        conn.close()
        return (0, 0)

    batch_size = max(1, get("images_per_batch", conn))
    done = failed = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        ref = reference_asset(conn, batch[0])
        prompt = build_batch_prompt(batch, model, ref is not None)

        if dry_run:
            print(f"\n--- batch di {len(batch)} · riferimento: "
                  f"{ref.relative_to(ROOT) if ref else 'nessuno'} ---")
            print(prompt)
            done += len(batch)
            continue

        print(f"Batch {i//batch_size + 1}: {len(batch)} immagini con {model} "
              f"in una sola richiesta (skill {skill})")
        try:
            task_id, attachments = asyncio.run(
                _render_batch(prompt, ref, skill, timeout_s, want=len(batch)))
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"[:200]
            for v in batch:
                conn.execute("UPDATE variants SET render_error=?, rendered_at=? WHERE id=?",
                             (msg, datetime.now().isoformat(timespec="seconds"), v["id"]))
            conn.commit()
            failed += len(batch)
            if not quiet:
                print(f"  ✗ batch fallito: {msg}")
            continue

        images = [a for a in attachments if _pick_image([a])]
        matched = _match(batch, images)
        for v in batch:
            img = matched.get(v["id"])
            if not img:
                failed += 1
                conn.execute("""UPDATE variants SET render_error=?, rendered_at=? WHERE id=?""",
                             ("nessuna immagine abbinabile nel batch",
                              datetime.now().isoformat(timespec="seconds"), v["id"]))
                conn.commit()
                if not quiet:
                    print(f"  ✗ [{v['id']}] nessuna immagine abbinabile")
                continue
            try:
                out = save_image(conn, v["id"], task_id, [img], model)
                done += 1
                if not quiet:
                    print(f"  ✓ [{v['id']}] {(v['headline'] or '')[:44]:<46} {out}")
            except Exception as e:
                failed += 1
                msg = f"{type(e).__name__}: {e}"[:200]
                conn.execute("UPDATE variants SET render_error=?, rendered_at=? WHERE id=?",
                             (msg, datetime.now().isoformat(timespec="seconds"), v["id"]))
                conn.commit()
                if not quiet:
                    print(f"  ✗ [{v['id']}] {msg}")
    conn.close()
    return (done, failed)


def status_report() -> int:
    conn = connect()
    migrate_images(conn)
    tot = conn.execute("SELECT COUNT(*) c FROM variants WHERE status IN ('proposed','approved')").fetchone()["c"]
    got = conn.execute("""SELECT COUNT(*) c FROM variants
                          WHERE asset_path IS NOT NULL AND asset_path != ''""").fetchone()["c"]
    err = conn.execute("SELECT COUNT(*) c FROM variants WHERE render_error IS NOT NULL").fetchone()["c"]
    print(f"Immagini varianti: {got}/{tot} · errori: {err}")
    for r in conn.execute("""SELECT id, image_model, asset_path, render_error FROM variants
                             WHERE rendered_at IS NOT NULL ORDER BY id"""):
        state = r["asset_path"] or f"✗ {r['render_error']}"
        print(f"  [{r['id']}] {(r['image_model'] or '—'):<14} {str(state)[:70]}")
    conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Immagini delle varianti via Manus + GPT Image 2")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--id", type=int)
    r.add_argument("--status", choices=("proposed", "approved"))
    r.add_argument("--force", action="store_true", help="rigenera anche chi ha già un'immagine")
    r.add_argument("--dry-run", action="store_true")
    rc = sub.add_parser("recover", help="salva l'immagine di un task Manus già eseguito")
    rc.add_argument("task_id")
    rc.add_argument("--id", type=int, required=True, help="id della variante")
    sub.add_parser("status")
    a = p.parse_args()

    if a.cmd == "status":
        return status_report()
    if a.cmd == "recover":
        return recover(a.task_id, a.id)
    done, failed = render(a.id, a.status, a.force, a.dry_run)
    if done == failed == 0:
        print("Niente da renderizzare (usa --force per rifare).")
        return 0
    if not a.dry_run:
        print(f"\n{done} immagini generate, {failed} fallite")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
