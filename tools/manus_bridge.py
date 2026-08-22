#!/usr/bin/env python3
"""
Bridge fra il Creative DB e Manus: genera varianti di un angolo che ha dati.

Il valore non è "mandare immagini a un'AI": è mandarle il contesto giusto.
Il brief contiene i dati di performance dell'angolo (dentro la sua classe di
evento, mai mescolando classi) e i creative di riferimento come allegati.

Gate: senza dati sufficienti la generazione è bloccata. Generare varianti da
2 lead significa moltiplicare rumore, non imparare. Si può disattivare con
`pipeline_config set generation_gate false`, ma è una scelta esplicita.

CLI:
  python tools/manus_bridge.py angles                # quali angoli superano il gate
  python tools/manus_bridge.py generate <angolo>
  python tools/manus_bridge.py generate <angolo> --dry-run   # stampa il brief, non chiama
  python tools/manus_bridge.py variants
  python tools/manus_bridge.py decide <id> approved|rejected [--note "..."]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from creative_db import EVENT_CLASSES, _event_label, connect, min_leads
from pipeline_config import ensure, get

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / ".secrets" / "mailift" / ".env")
load_dotenv(ROOT / ".env")

REAL_CLASSES = ("web", "leadform")
POLL_INTERVAL_S = 10
# Quanto tollerare il 404 di task.detail subito dopo task.create.
NOT_FOUND_GRACE_S = 90

# Le 6 famiglie di formato. Sono l'asse su cui si scala un angolo che vince:
# Andromeda collassa le creative che condividono formato+voce+messaggio in una
# sola entità e affama i gemelli, quindi ricolorare lo stesso messaggio non apre
# tasche nuove — cambiare formato sì.
FORMAT_FAMILIES = {
    "statica":          ("brand", "Statica testuale: il testo è il girato, il colore è cosmetico."),
    "carosello":        ("brand", "Ragionamento a step: meccanismo, case study, '5 errori'."),
    "native":           ("nessuna", "Pattern interrupt: POV raw, meme, testo semplice."),
    "video-parlato":    ("brand", "Founder in camera: contrarian, rant, teardown."),
    "ugc":              ("cliente", "Voce del cliente: testimonial, scettico convertito."),
    "screen-recording": ("voce-off", "Prodotto/dashboard Klaviyo reale in azione."),
}

# Cosa può diventare un'immagine generata e cosa no.
# screen-recording è escluso di proposito: una dashboard Klaviyo finta generata
# con l'AI distrugge la credibilità proprio dove Mailift ha il vantaggio vero
# (account reali). Quelle vanno registrate, non disegnate.
RENDERABLE_FAMILIES = ("statica", "native")


class GateBlocked(RuntimeError):
    pass


# ── analisi angoli ────────────────────────────────────────────────────────────

def angle_stats(conn) -> list[dict]:
    """Performance per (angolo, classe evento). Solo classi con lead veri."""
    rows = conn.execute("""
        SELECT c.angle, c.awareness_stage, c.hook_type,
               a.optimization_goal, a.custom_event_type,
               COUNT(DISTINCT c.creative_id) n,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        WHERE c.angle IS NOT NULL AND c.angle != ''
        GROUP BY c.angle, a.optimization_goal, a.custom_event_type
    """).fetchall()

    agg: dict[tuple, dict] = {}
    for r in rows:
        klass = EVENT_CLASSES.get(_event_label(r), "?")
        if klass not in REAL_CLASSES:
            continue
        k = (r["angle"], klass)
        e = agg.setdefault(k, {"angle": r["angle"], "klass": klass, "n": 0,
                               "spend": 0.0, "leads": 0})
        e["n"] += r["n"]
        e["spend"] += r["spend"] or 0
        e["leads"] += r["leads"] or 0

    T = min_leads()
    out = []
    for e in agg.values():
        e["cpl"] = round(e["spend"] / e["leads"], 2) if e["leads"] else None
        e["enough"] = e["leads"] >= T
        out.append(e)
    return sorted(out, key=lambda x: -x["leads"])


def eligible_angles(conn) -> list[dict]:
    return [a for a in angle_stats(conn) if a["enough"]]


def check_gate(conn, angle: str) -> dict:
    """Ritorna la riga di stats se l'angolo può essere generato, altrimenti alza."""
    stats = [a for a in angle_stats(conn) if a["angle"] == angle]
    if not stats:
        raise GateBlocked(
            f"L'angolo '{angle}' non ha creative classificati in una classe con lead veri "
            f"(web/leadform). Lancia prima: creative_classifier.py classify")
    best = max(stats, key=lambda x: x["leads"])
    if not get("generation_gate", conn):
        best["gate_bypassed"] = True
        return best
    if not best["enough"]:
        raise GateBlocked(
            f"'{angle}' ha {best['leads']} lead (classe {best['klass']}), sotto la soglia "
            f"di {min_leads()}. Generare varianti da questi numeri significa moltiplicare "
            f"rumore.\nOpzioni: concentra la spesa su questo angolo finché raggiunge la "
            f"soglia, abbassa min_leads_for_verdict, oppure disattiva generation_gate "
            f"sapendo cosa comporta.")
    return best


# ── brief ─────────────────────────────────────────────────────────────────────

def reference_creatives(conn, angle: str, klass: str, limit: int = 3) -> list[dict]:
    """I creative dell'angolo con più lead: sono il riferimento da variare."""
    rows = conn.execute("""
        SELECT c.creative_id, c.ad_name, c.headline, c.body, c.cta, c.asset_path,
               c.visual_note, c.hook_type, c.awareness_stage,
               a.optimization_goal, a.custom_event_type,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        WHERE c.angle = ?
        GROUP BY c.creative_id
        ORDER BY leads DESC, spend DESC
    """, (angle,)).fetchall()

    out = []
    for r in rows:
        if EVENT_CLASSES.get(_event_label(r), "?") != klass:
            continue
        d = {k: r[k] for k in r.keys()}
        # Lo storico Meta non dice il formato: sono immagini singole, quindi statiche.
        d.setdefault("format_family", "statica")
        out.append(d)
        if len(out) >= limit:
            break
    return out


def losers(conn, angle: str, klass: str, limit: int = 3) -> list[dict]:
    """Creative dello stesso angolo che hanno speso senza produrre lead."""
    rows = conn.execute("""
        SELECT c.ad_name, c.headline, a.optimization_goal, a.custom_event_type,
               ROUND(SUM(d.spend),2) spend, SUM(d.leads) leads
        FROM creatives c
        JOIN daily_results d USING (creative_id)
        LEFT JOIN adsets a ON a.adset_id = c.adset_id
        WHERE c.angle = ?
        GROUP BY c.creative_id
        HAVING leads = 0 AND spend > 10
        ORDER BY spend DESC
    """, (angle,)).fetchall()
    return [dict(r) for r in rows if EVENT_CLASSES.get(_event_label(r), "?") == klass][:limit]


def session_kickoff(skill: str) -> str:
    """Contesto fisso della conversazione: si paga una volta, non a ogni richiesta."""
    fam = "\n".join(f"  - {k} (voce tipica: {v[0]}): {v[1]}" for k, v in FORMAT_FAMILIES.items())
    return f"""Sei il direttore creativo di Mailift, agenzia italiana di email marketing per
eCommerce DTC su Shopify e Klaviyo (clienti da €25k–300k/mese di fatturato).

Questa conversazione resterà aperta: ti manderò più richieste di seguito. Tieni
il contesto, non ripartire da capo ogni volta.

REGOLA MADRE (Andromeda, il motore di retrieval di Meta)
È la creatività a fare il targeting, non l'audience. Andromeda vede come STESSA
ENTITÀ le creative che condividono formato, voce e messaggio: le collassa, sceglie
un gemello e affama gli altri. Ricolorare lo stesso messaggio o riscriverlo con
parole diverse NON apre tasche nuove ed è tempo sprecato.
Un'entità è nuova se cambia almeno uno di questi assi, meglio più di uno:
  1. FORMATO   2. VOCE   3. ANGOLO (il dolore attaccato)

FAMIGLIE DI FORMATO
{fam}

REGOLE DI QUALITÀ
- Italiano, tono diretto e concreto. Parli al proprietario dell'eCommerce, non a un marketer.
- Meno immagine, più headline. Un solo elemento visivo chiaro batte il caos.
- Niente dashboard Klaviyo finte generate con l'AI: Mailift ha account veri, un
  finto distrugge la credibilità. Se un formato richiede un dato reale, scrivi il
  brief di produzione e dichiara che va registrato, non disegnato.
- Nessuna promessa di guadagno garantito, nessun numero non fornito da me.

Rispondi "pronto" e aspetta la prima richiesta."""


def build_brief(conn, angle: str, stats: dict, refs: list[dict],
                lost: list[dict], n_variants: int) -> str:
    from creative_classifier import ANGLES, AWARENESS, HOOKS

    dest = ("una landing sul sito (report.mailift.com, calcolatore ROI)"
            if stats["klass"] == "web" else "un modulo istantaneo dentro Meta")

    ref_txt = "\n\n".join(
        f"RIFERIMENTO {i+1} — {r['ad_name']}\n"
        f"  Headline: {r['headline'] or '(nessuna)'}\n"
        f"  Corpo: {(r['body'] or '(nessuno)')[:300]}\n"
        f"  CTA: {r['cta'] or '(nessuna)'}\n"
        f"  Visual: {r['visual_note'] or 'vedi allegato'}\n"
        f"  Hook: {r['hook_type']} · Awareness: {r['awareness_stage']}\n"
        f"  Risultato: €{r['spend']:.0f} spesi, {r['leads']} lead"
        + (f", CPL €{r['spend']/r['leads']:.2f}" if r["leads"] else "")
        for i, r in enumerate(refs))

    lost_txt = ("\n".join(
        f"  - \"{(l['headline'] or l['ad_name'])[:90]}\" → €{l['spend']:.0f} spesi, 0 lead"
        for l in lost) or "  (nessuno rilevante)")

    ref_families = sorted({r.get("format_family") or "statica" for r in refs})

    return f"""RICHIESTA: {n_variants} creative NUOVE ENTITÀ per l'angolo "{angle}".

ANGOLO CHE HA I DATI
{ANGLES.get(angle, angle)}

PERCHÉ QUESTO ANGOLO (classe evento: {stats['klass']} — destinazione: {dest})
  Creative testati: {stats['n']} · Spesa: €{stats['spend']:.0f} · Lead: {stats['leads']} ·
  CPL: {"€%.2f" % stats['cpl'] if stats['cpl'] else "—"}
Questo angolo ha prodotto lead veri, quindi il messaggio regge. Non va cambiato:
va PORTATO SU FORMATI DIVERSI, perché la tasca che risponde al formato attuale
({", ".join(ref_families)}) satura.

COSA HA FUNZIONATO — allegati in coda le immagini di questi annunci
{ref_txt}

COSA NON HA FUNZIONATO — stesso angolo, zero lead
{lost_txt}

COME DEVONO ESSERE LE {n_variants} CREATIVE
- Ognuna su una FAMIGLIA DI FORMATO DIVERSA dalle altre e diversa da {", ".join(ref_families)}.
  Se le famiglie disponibili non bastano, cambia anche la VOCE.
- NON voglio micro-variazioni del riferimento: stesso messaggio ricolorato o
  riscritto con sinonimi è la stessa entità, Andromeda la ingoia. Se ti accorgi di
  stare "facendo sembrare diverso lo stesso annuncio", hai sbagliato asse.
- L'angolo resta "{angle}" in tutte: cambia il MODO di raccontarlo, non il dolore.
- La destinazione è {dest}: la CTA deve essere coerente.
- Per i formati che richiedono girato o dati reali (video-parlato, ugc,
  screen-recording): NON inventare l'asset. Scrivi il brief di produzione in
  `visual_brief` e metti `"da_produrre": true`.

VOCABOLARIO (usa solo questi valori)
  format_family: {", ".join(FORMAT_FAMILIES)}
  voice: brand, cliente, voce-off, nessuna
  hook_type: {", ".join(HOOKS)}
  awareness_stage: {", ".join(AWARENESS)}

OUTPUT — UN SOLO blocco ```json con questo schema, senza testo prima o dopo:

```json
{{
  "variants": [
    {{
      "format_family": "una del vocabolario",
      "voice": "una del vocabolario",
      "da_produrre": false,
      "headline": "max 60 caratteri",
      "body": "2-4 frasi",
      "cta": "es. Scopri il Metodo Mailift",
      "hook_type": "uno del vocabolario",
      "awareness_stage": "uno del vocabolario",
      "visual_brief": "cosa mostrare / come girarlo, 1-2 frasi",
      "rationale": "su quali assi è un'entità diversa dal riferimento, e quale tasca dovrebbe aprire"
    }}
  ]
}}
```
Esattamente {n_variants} creative, ognuna su una famiglia diversa."""


# ── Manus ─────────────────────────────────────────────────────────────────────

async def _upload(client, path: Path) -> str:
    from manus_mcp.schemas.files import FileCreateRequest, FileCreateResponse
    res = await client.call("POST", "/v2/file.upload",
                            json_body=FileCreateRequest(filename=path.name),
                            response_model=FileCreateResponse)
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    await client.put_raw(res.upload_url, path.read_bytes(), ctype)
    return res.file.id


async def _fetch_answer(client, task_id: str) -> str | None:
    """L'ultimo messaggio dell'assistente, se già scritto."""
    from manus_mcp.schemas.tasks import TaskListMessagesQuery, TaskListMessagesResponse
    msgs = await client.call(
        "GET", "/v2/task.listMessages",
        params=TaskListMessagesQuery(task_id=task_id, order="desc", limit=20).model_dump(exclude_none=True),
        response_model=TaskListMessagesResponse)
    for m in msgs.messages or []:
        if m.assistant_message and m.assistant_message.content:
            return m.assistant_message.content
    return None


async def _wait_for_answer(client, task_id: str, timeout_s: int) -> str:
    """Attende il messaggio, non lo stato.

    Due comportamenti reali dell'API imparati sul campo:
    1) task.detail risponde 404 per qualche secondo dopo task.create — il task
       esiste (l'id è già stato restituito) ma non è ancora propagato.
    2) lo stato passa a 'stopped' prima che la risposta sia leggibile, quindi
       uscire appena status != running lascia le mani vuote su un task pagato.
    Per questo la condizione di uscita è "c'è la risposta", non "lo stato dice X".
    """
    from manus_mcp.client import ManusApiError
    from manus_mcp.schemas.tasks import TaskDetailQuery, TaskDetailResponse

    waited = 0
    status = "?"
    while True:
        try:
            det = await client.call(
                "GET", "/v2/task.detail",
                params=TaskDetailQuery(task_id=task_id).model_dump(exclude_none=True),
                response_model=TaskDetailResponse)
            status = det.task.status
            if status == "error":
                raise RuntimeError(f"task Manus in errore (id {task_id})")
            answer = await _fetch_answer(client, task_id)
            if answer:
                return answer
        except ManusApiError as e:
            # 404 iniziale: il task non è ancora propagato, non è sparito.
            if getattr(e, "http_status", None) != 404 and "not_found" not in str(e):
                raise
            if waited > NOT_FOUND_GRACE_S:
                raise RuntimeError(
                    f"task {task_id} ancora not_found dopo {waited}s") from e

        if waited >= timeout_s:
            raise TimeoutError(
                f"nessuna risposta dopo {timeout_s}s (stato: {status}).\n"
                f"Il task esiste ed è già pagato: recuperalo con\n"
                f"  python tools/manus_bridge.py recover {task_id} <angolo>")
        await asyncio.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
        if waited % 60 == 0:
            print(f"  …{waited}s (stato: {status})")


def _client():
    from manus_mcp.client import ManusClient
    key = os.environ.get("MANUS_API_KEY")
    if not key:
        raise RuntimeError("MANUS_API_KEY non trovata in .env")
    return ManusClient(api_key=key)


async def _run_manus(brief: str, assets: list[Path], timeout_s: int,
                     skill: str) -> tuple[str, str]:
    """Manda il brief nella conversazione condivisa. Ritorna (task_id, testo).

    Una sola conversazione riusata: un task nuovo per richiesta ricaricherebbe
    skill e contesto da zero ogni volta, pagandolo in crediti e in attesa.
    """
    from manus_mcp.schemas.tasks import FilePart, TextPart

    from manus_session import ensure_session, send_and_wait

    client = _client()
    try:
        task_id, _ = await ensure_session(client, skill, session_kickoff(skill))
        parts = [TextPart(type="text", text=brief)]
        for a in assets:
            parts.append(FilePart(type="file", file_id=await _upload(client, a)))

        def has_variants(text, _images) -> bool:
            if not text:
                return False
            try:
                parse_variants(text)
                return True
            except ValueError:
                return False   # è un messaggio intermedio: continua ad aspettare

        text, _att = await send_and_wait(client, task_id, parts, timeout_s,
                                         ready=has_variants)
        if not text:
            raise RuntimeError("nessuna risposta testuale dalla conversazione")
        return task_id, text
    finally:
        await client.aclose()


async def _recover(task_id: str) -> str:
    client = _client()
    try:
        answer = await _fetch_answer(client, task_id)
        if not answer:
            raise RuntimeError(f"il task {task_id} non ha (ancora) una risposta")
        return answer
    finally:
        await client.aclose()


def _loads_lenient(raw: str):
    """json.loads, ma tollerando la virgola finale prima di } o ].

    I modelli la producono spesso. Rifiutare per una virgola una risposta che è
    già stata pagata in crediti è uno spreco, non rigore.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(re.sub(r",\s*([}\]])", r"\1", raw))


def parse_variants(text: str) -> list[dict]:
    """Estrae il blocco JSON. Manus può accompagnarlo con prosa: prendiamo il blocco."""
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = blocks or [text]
    for c in candidates:
        try:
            data = _loads_lenient(c)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("variants"), list):
            return data["variants"]
    raise ValueError("nessun JSON con chiave 'variants' nella risposta di Manus")


def migrate_entities(conn) -> None:
    """format_family e voice: senza, non si può distinguere un'entità nuova da
    una micro-variazione, che è l'unica distinzione che conta per lo scaling."""
    ensure(conn)
    have = {r["name"] for r in conn.execute("PRAGMA table_info(variants)")}
    for col, typ in (("format_family", "TEXT"), ("voice", "TEXT"), ("da_produrre", "INTEGER")):
        if col not in have:
            conn.execute(f"ALTER TABLE variants ADD COLUMN {col} {typ}")
    conn.commit()


def save_variants(conn, angle: str, stats: dict, parent_id: str | None,
                  task_id: str, variants: list[dict]) -> int:
    migrate_entities(conn)
    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    for v in variants:
        fam = v.get("format_family") or "statica"
        # Il vincolo di famiglia è strutturale e Manus non può annullarlo: un
        # carosello sono N slide, un UGC va girato. Dichiarando `da_produrre: false`
        # può solo sbagliarsi. Quindi il flag si può solo aggiungere, mai togliere.
        prod = bool(v.get("da_produrre")) or fam not in RENDERABLE_FAMILIES
        conn.execute("""INSERT INTO variants (parent_creative_id, angle, awareness_stage,
                        hook_type, headline, body, cta, rationale, source, manus_task_id,
                        status, created_at, format_family, voice, da_produrre)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (parent_id, angle, v.get("awareness_stage"), v.get("hook_type"),
                      v.get("headline"), v.get("body"), v.get("cta"),
                      json.dumps({"rationale": v.get("rationale"),
                                  "visual_brief": v.get("visual_brief")}, ensure_ascii=False),
                      "manus", task_id, "proposed", now, fam, v.get("voice"), int(bool(prod))))
        n += 1
    conn.commit()
    return n


def generate(angle: str, dry_run: bool) -> int:
    conn = connect()
    ensure(conn)
    try:
        stats = check_gate(conn, angle)
    except GateBlocked as e:
        print(f"⛔ Gate: {e}")
        conn.close()
        return 2

    if stats.get("gate_bypassed"):
        print(f"⚠️  generation_gate disattivato: procedo con {stats['leads']} lead "
              f"(soglia {min_leads()}). I risultati non saranno interpretabili.")

    n_var = get("variants_per_run", conn)
    refs = reference_creatives(conn, angle, stats["klass"])
    lost = losers(conn, angle, stats["klass"])
    brief = build_brief(conn, angle, stats, refs, lost, n_var)
    assets = [ROOT / r["asset_path"] for r in refs if r["asset_path"]
              and (ROOT / r["asset_path"]).exists()]

    if dry_run:
        print(brief)
        print(f"\n--- allegati: {len(assets)} ---")
        for a in assets:
            print(f"  {a.relative_to(ROOT)}")
        conn.close()
        return 0

    print(f"Genero {n_var} varianti per '{angle}' (classe {stats['klass']}, "
          f"{stats['leads']} lead) con {len(assets)} riferimenti visivi")
    try:
        task_id, text = asyncio.run(_run_manus(brief, assets, get("manus_poll_timeout_s", conn),
                                              get("manus_ad_skill", conn)))
        variants = parse_variants(text)
    except Exception as e:
        print(f"✗ {type(e).__name__}: {e}")
        conn.close()
        return 1

    n = save_variants(conn, angle, stats, refs[0]["creative_id"] if refs else None,
                      task_id, variants)
    conn.close()
    print(f"\n✓ {n} varianti salvate con status 'proposed'.")
    print("  Rivedile con: python tools/manus_bridge.py variants")
    return 0


# ── varianti ──────────────────────────────────────────────────────────────────

def recover(task_id: str, angle: str) -> int:
    """Salva le varianti di un task Manus già eseguito (es. dopo un timeout)."""
    conn = connect()
    ensure(conn)
    stats = [a for a in angle_stats(conn) if a["angle"] == angle]
    if not stats:
        print(f"⛔ angolo '{angle}' sconosciuto o senza dati")
        conn.close()
        return 2
    best = max(stats, key=lambda x: x["leads"])
    try:
        text = asyncio.run(_recover(task_id))
        variants = parse_variants(text)
    except Exception as e:
        print(f"✗ {type(e).__name__}: {e}")
        conn.close()
        return 1
    refs = reference_creatives(conn, angle, best["klass"])
    n = save_variants(conn, angle, best, refs[0]["creative_id"] if refs else None,
                      task_id, variants)
    conn.close()
    print(f"✓ {n} varianti recuperate dal task {task_id} e salvate come 'proposed'.")
    return 0


def list_variants(status: str | None) -> int:
    conn = connect()
    ensure(conn)
    q = "SELECT * FROM variants"
    args = ()
    if status:
        q += " WHERE status=?"
        args = (status,)
    rows = conn.execute(q + " ORDER BY id DESC", args).fetchall()
    conn.close()

    if not rows:
        print("Nessuna variante." + ("" if status else " Generane con: generate <angolo>"))
        return 0
    for r in rows:
        extra = json.loads(r["rationale"] or "{}")
        print(f"\n[{r['id']}] {r['status'].upper()} · angolo {r['angle']} · {r['created_at']}")
        print(f"  Headline: {r['headline']}")
        print(f"  Corpo:    {(r['body'] or '')[:150]}")
        print(f"  CTA:      {r['cta']} · hook {r['hook_type']} · {r['awareness_stage']}")
        if extra.get("visual_brief"):
            print(f"  Visual:   {extra['visual_brief'][:120]}")
        if extra.get("rationale"):
            print(f"  Perché:   {extra['rationale'][:130]}")
    return 0


def decide(vid: int, status: str, note: str | None) -> int:
    if status not in ("approved", "rejected"):
        print("Stato ammesso: approved | rejected")
        return 1
    conn = connect()
    ensure(conn)
    cur = conn.execute("""UPDATE variants SET status=?, decided_at=?, decided_note=?
                          WHERE id=? AND status='proposed'""",
                       (status, datetime.now().isoformat(timespec="seconds"), note, vid))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        print(f"Variante {vid} non trovata o già decisa.")
        return 1
    print(f"Variante {vid} → {status}")
    return 0


def show_angles() -> int:
    conn = connect()
    ensure(conn)
    stats = angle_stats(conn)
    conn.close()
    if not stats:
        print("Nessun angolo classificato in una classe con lead veri.")
        print("Lancia: python tools/creative_classifier.py classify")
        return 1
    T = min_leads()
    print(f"Soglia attuale: {T} lead · gate {'ATTIVO' if get('generation_gate') else 'DISATTIVO'}\n")
    print(f"{'ANGOLO':<24} {'CLASSE':<10} {'N':>3} {'SPESA':>8} {'LEAD':>5} {'CPL':>9}  GENERABILE")
    for s in stats:
        cpl = f"€{s['cpl']:.2f}" if s["cpl"] else "—"
        ok = "sì" if s["enough"] else f"no ({s['leads']}/{T})"
        print(f"{s['angle']:<24} {s['klass']:<10} {s['n']:>3} €{s['spend']:>7.0f} "
              f"{s['leads']:>5} {cpl:>9}  {ok}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Bridge Creative DB → Manus")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("angles")
    g = sub.add_parser("generate"); g.add_argument("angle"); g.add_argument("--dry-run", action="store_true")
    rc = sub.add_parser("recover", help="salva le varianti di un task Manus già eseguito")
    rc.add_argument("task_id"); rc.add_argument("angle")
    v = sub.add_parser("variants"); v.add_argument("--status")
    d = sub.add_parser("decide"); d.add_argument("id", type=int); d.add_argument("status")
    d.add_argument("--note")
    a = p.parse_args()

    if a.cmd == "angles":
        return show_angles()
    if a.cmd == "generate":
        return generate(a.angle, a.dry_run)
    if a.cmd == "recover":
        return recover(a.task_id, a.angle)
    if a.cmd == "variants":
        return list_variants(a.status)
    if a.cmd == "decide":
        return decide(a.id, a.status, a.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
