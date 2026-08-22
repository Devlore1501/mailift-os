#!/usr/bin/env python3
"""
Conversazione Manus persistente e condivisa.

Perché una sola conversazione invece di un task per richiesta: ogni task nuovo
riparte da zero — Manus rilegge il contesto, ricarica la skill, ripaga il setup.
Tenendo un task vivo e mandandogli messaggi, il contesto (angolo, riferimenti,
stile già concordato) resta caldo e le richieste successive costano e durano meno.

Il task_id vive in config (`manus_session_task_id`), quindi sopravvive ai riavvii.

CLI:
  python tools/manus_session.py show
  python tools/manus_session.py reset     # forza una conversazione nuova
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from creative_db import connect
from pipeline_config import ensure, get, reset, set_

ROOT = Path(__file__).resolve().parent.parent

POLL_INTERVAL_S = 10
NOT_FOUND_GRACE_S = 90
# Manus scrive messaggi intermedi prima di consegnare: dopo 'stopped' si guarda
# ancora un po', perché lo stato precede la scrittura del messaggio.
STOPPED_GRACE_S = 45


class SessionExpired(RuntimeError):
    """Il task salvato non è più utilizzabile: se ne apre uno nuovo."""


async def _message_ids(client, task_id: str) -> set[str]:
    from manus_mcp.schemas.tasks import TaskListMessagesQuery, TaskListMessagesResponse
    msgs = await client.call(
        "GET", "/v2/task.listMessages",
        params=TaskListMessagesQuery(task_id=task_id, order="desc",
                                     limit=50).model_dump(exclude_none=True),
        response_model=TaskListMessagesResponse)
    return {m.id for m in (msgs.messages or [])}


async def _new_assistant(client, task_id: str, seen: set[str]) -> tuple[str | None, list]:
    """Testo e allegati dei soli messaggi comparsi dopo `seen`."""
    from manus_mcp.schemas.tasks import TaskListMessagesQuery, TaskListMessagesResponse
    msgs = await client.call(
        "GET", "/v2/task.listMessages",
        params=TaskListMessagesQuery(task_id=task_id, order="desc",
                                     limit=50).model_dump(exclude_none=True),
        response_model=TaskListMessagesResponse)
    text, attachments = None, []
    for m in msgs.messages or []:
        if m.id in seen or not m.assistant_message:
            continue
        if m.assistant_message.attachments:
            attachments.extend(m.assistant_message.attachments)
        if m.assistant_message.content and text is None:
            text = m.assistant_message.content
    return text, attachments


async def ensure_session(client, skill: str, kickoff: str) -> tuple[str, bool]:
    """Ritorna (task_id, creato_ora). Riusa la conversazione salvata se è viva."""
    from manus_mcp.client import ManusApiError
    from manus_mcp.schemas.tasks import (MessageBlock, TaskCreateRequest, TaskCreateResponse,
                                         TaskDetailQuery, TaskDetailResponse, TextPart)

    conn = connect()
    ensure(conn)
    saved = get("manus_session_task_id", conn)
    conn.close()

    if saved:
        try:
            await client.call("GET", "/v2/task.detail",
                              params=TaskDetailQuery(task_id=saved).model_dump(exclude_none=True),
                              response_model=TaskDetailResponse)
            return saved, False
        except ManusApiError as e:
            if getattr(e, "http_status", None) != 404 and "not_found" not in str(e):
                raise
            print(f"  conversazione {saved} non più valida: ne apro una nuova")

    created = await client.call(
        "POST", "/v2/task.create",
        json_body=TaskCreateRequest(
            message=MessageBlock(content=[TextPart(type="text", text=kickoff)],
                                 force_skills=[skill]),
            title="Mailift · creative (sessione)"),
        response_model=TaskCreateResponse)
    conn = connect()
    set_("manus_session_task_id", created.task_id, conn)
    conn.close()
    print(f"  nuova conversazione Manus: {created.task_id}  {created.task_url or ''}")

    # Aspettare la risposta al kickoff non è cortesia: se mandiamo subito il brief,
    # il "pronto" arriva dopo il nostro watermark e viene scambiato per la risposta.
    await _wait_kickoff(client, created.task_id)
    return created.task_id, True


async def _wait_kickoff(client, task_id: str, timeout_s: int = 180) -> None:
    from manus_mcp.client import ManusApiError
    waited = 0
    while waited < timeout_s:
        try:
            text, _ = await _new_assistant(client, task_id, set())
            if text:
                return
        except ManusApiError as e:
            if getattr(e, "http_status", None) != 404 and "not_found" not in str(e):
                raise
        await asyncio.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
    print("  (nessuna conferma al kickoff, procedo comunque)")


async def send_and_wait(client, task_id: str, parts: list, timeout_s: int,
                        want_images: int = 0, ready=None) -> tuple[str | None, list]:
    """Manda un messaggio nella conversazione e attende la risposta NUOVA.

    Distinguere "nuovo" da "già presente" è obbligatorio in una conversazione
    riusata: senza watermark sugli id si rileggerebbe la risposta precedente e
    si crederebbe di avere un risultato fresco.

    La condizione d'uscita non è "è arrivato del testo": Manus annuncia il lavoro
    ("procedo...") molto prima di consegnarlo. Chi chiama dice cosa aspetta:
      want_images=N  → almeno N allegati immagine
      ready(text, images) → predicato esplicito (es. "il testo contiene il JSON")
    """
    from manus_mcp.client import ManusApiError
    from manus_mcp.schemas.tasks import (MessageBlock, TaskDetailQuery, TaskDetailResponse,
                                         TaskSendMessageRequest, TaskSendMessageResponse)

    seen = await _message_ids(client, task_id)
    await client.call("POST", "/v2/task.sendMessage",
                      json_body=TaskSendMessageRequest(task_id=task_id,
                                                       message=MessageBlock(content=parts)),
                      response_model=TaskSendMessageResponse)

    waited = 0
    stopped_for = 0
    status = "?"
    while True:
        try:
            det = await client.call(
                "GET", "/v2/task.detail",
                params=TaskDetailQuery(task_id=task_id).model_dump(exclude_none=True),
                response_model=TaskDetailResponse)
            status = det.task.status
            if status == "error":
                raise RuntimeError(f"conversazione Manus in errore ({task_id})")

            text, attachments = await _new_assistant(client, task_id, seen)
            images = [a for a in attachments if _is_image(a)]

            if want_images:
                if len(images) >= want_images:
                    return text, attachments
            elif ready:
                if ready(text, images):
                    return text, attachments
            elif text:
                return text, attachments

            if status == "stopped":
                stopped_for += POLL_INTERVAL_S
                if stopped_for > STOPPED_GRACE_S:
                    if want_images and images:
                        # Ne ha consegnate meno del richiesto: meglio poche vere
                        # che un errore che butta via lavoro già pagato.
                        return text, attachments
                    if ready and text:
                        # Ha finito e qualcosa ha scritto: che sia utile lo decide
                        # chi chiama, con un errore leggibile invece che generico.
                        return text, attachments
                    raise RuntimeError(
                        f"conversazione conclusa senza risultato utile "
                        f"({len(images)}/{want_images} immagini)")
            else:
                stopped_for = 0
        except ManusApiError as e:
            if getattr(e, "http_status", None) != 404 and "not_found" not in str(e):
                raise
            if waited > NOT_FOUND_GRACE_S:
                raise SessionExpired(f"task {task_id} non trovato") from e

        if waited >= timeout_s:
            raise TimeoutError(f"nessuna risposta dopo {timeout_s}s (stato: {status}) "
                               f"nella conversazione {task_id}")
        await asyncio.sleep(POLL_INTERVAL_S)
        waited += POLL_INTERVAL_S
        if waited % 60 == 0:
            got = len([a for a in (await _new_assistant(client, task_id, seen))[1] if _is_image(a)])
            extra = f" · {got}/{want_images} immagini" if want_images else ""
            print(f"    …{waited}s (stato: {status}{extra})")


def _is_image(a) -> bool:
    ctype = (getattr(a, "content_type", "") or "").lower()
    name = (getattr(a, "filename", "") or "").lower()
    return ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp"))


def main() -> int:
    p = argparse.ArgumentParser(description="Conversazione Manus persistente")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("reset")
    a = p.parse_args()

    if a.cmd == "show":
        tid = get("manus_session_task_id")
        print(f"Conversazione attiva: {tid or '(nessuna, la prossima richiesta la crea)'}")
        if tid:
            print(f"  https://manus.im/app/{tid}")
    elif a.cmd == "reset":
        reset("manus_session_task_id")
        print("Sessione azzerata: la prossima richiesta aprirà una conversazione nuova.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
