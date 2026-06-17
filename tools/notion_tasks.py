"""
Wrapper Notion API per il workflow Daily Inbox Triage e per la lettura/triage
dei task dal database Tasks_Mailift.

Funzioni esposte:
    create_task(client, **kwargs)  -> crea una pagina nel data source Tasks_Mailift
    list_open_tasks(only_lorenzo, include_unassigned, page_size) -> list[dict]
    get_client()                   -> client Notion autenticato

Schema Tasks_Mailift verificato 2026-04-08:
    Name (title), Assign (person), Status (select), Due Date (date),
    Categoria (select), Priorita (select), Cliente (relation)

NOTA: dalla Notion API version 2025-09-03 le proprieta' vivono sui
"data source" (collection) e non sul database padre. Per creare pagine
serve il NOTION_TASKS_DATA_SOURCE_ID, non NOTION_TASKS_DB_ID. Vedi .env.

L'integration Notion deve essere stata aggiunta a Tasks_Mailift per
leggere/scrivere.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from notion_client import Client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Categorie valide nel select Tasks_Mailift.Categoria
CATEGORIE = {"Strategia", "Copy", "Design", "Tecnico", "Reportistica", "Altro"}
PRIORITA = {"Alta", "Media", "Bassa"}
STATUS_DEFAULT = "To-do"

# Status considerati "aperti" per list_open_tasks
OPEN_STATUSES = ("To-do", "In corso")

# Ranking priorita' per ordinamento (piu' basso = piu' urgente)
PRIORITY_RANK = {"Alta": 0, "Media": 1, "Bassa": 2, None: 3}


def get_client() -> Client:
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY mancante in .env. Crea un'integration su https://www.notion.so/my-integrations")
    return Client(auth=api_key)


def _to_property_payload(
    *,
    name: str,
    assign_user_ids: list[str],
    status: str,
    due_date: Optional[str],
    categoria: str,
    priorita: str,
) -> dict:
    if categoria not in CATEGORIE:
        categoria = "Altro"
    if priorita not in PRIORITA:
        priorita = "Media"

    props: dict = {
        "Name": {"title": [{"text": {"content": name[:2000]}}]},
        "Assign": {"people": [{"id": uid} for uid in assign_user_ids]},
        "Status": {"status": {"name": status}},
        "Categoria": {"select": {"name": categoria}},
        "Priorità": {"select": {"name": priorita}},
    }
    if due_date:
        props["Due Date"] = {"date": {"start": due_date}}
    return props


def _body_blocks(
    *,
    permalink: str,
    sender: str,
    account_label: str,
    received_at: str,
    context: str,
) -> list[dict]:
    """Costruisce i blocchi del body della pagina (header con link Gmail + contesto)."""
    blocks: list[dict] = []
    # Header con link Gmail
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": "📧 ", "link": None}},
                {"type": "text", "text": {"content": "Apri thread Gmail", "link": {"url": permalink}}},
            ],
        },
    })
    blocks.append({
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Da: {sender}"}}]},
    })
    blocks.append({
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Account: {account_label}"}}]},
    })
    blocks.append({
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Data: {received_at}"}}]},
    })
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    if context:
        # Splitta il contesto in paragrafi se contiene newline
        for chunk in context.split("\n"):
            if not chunk.strip():
                continue
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk[:1900]}}]},
            })
    return blocks


def create_task(
    client: Client,
    *,
    data_source_id: str,
    name: str,
    assign_user_ids: list[str],
    categoria: str,
    priorita: str,
    due_date: Optional[str],
    permalink: str,
    sender: str,
    account_label: str,
    received_at: str,
    context: str,
    status: str = STATUS_DEFAULT,
) -> dict:
    """Crea una pagina nel data source Tasks_Mailift. Ritorna la response Notion (con id e url)."""
    props = _to_property_payload(
        name=name,
        assign_user_ids=assign_user_ids,
        status=status,
        due_date=due_date,
        categoria=categoria,
        priorita=priorita,
    )
    children = _body_blocks(
        permalink=permalink,
        sender=sender,
        account_label=account_label,
        received_at=received_at,
        context=context,
    )
    return client.pages.create(
        parent={"type": "data_source_id", "data_source_id": data_source_id},
        properties=props,
        children=children,
    )


# ─── Update task ─────────────────────────────────────────────────────────────


def update_task_status(
    page_id: str,
    new_status: str,
    client: Optional[Client] = None,
) -> dict:
    """Aggiorna lo Status di un task su Notion.

    Status validi (verificati 2026-04-08): "To-do", "In corso", "In approvazione",
    "Completato".
    """
    if client is None:
        client = get_client()
    return client.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": new_status}}},
    )


def mark_task_done(page_id: str, client: Optional[Client] = None) -> dict:
    """Shortcut: marca un task come Completato."""
    return update_task_status(page_id, "Completato", client=client)


def mark_tasks_done_batch(
    page_ids: list[str],
    client: Optional[Client] = None,
) -> dict:
    """Marca una lista di task come Completati. Ritorna report con success/error per page_id.

    Non solleva su errore singolo: continua, raccoglie e ritorna il riepilogo.
    """
    if client is None:
        client = get_client()
    report: dict[str, Any] = {
        "total": len(page_ids),
        "succeeded": [],
        "failed": [],
    }
    for pid in page_ids:
        try:
            mark_task_done(pid, client=client)
            report["succeeded"].append(pid)
        except Exception as exc:  # noqa: BLE001
            report["failed"].append({"id": pid, "error": f"{type(exc).__name__}: {exc}"})
    return report


def update_task_properties(
    page_id: str,
    *,
    name: Optional[str] = None,
    status: Optional[str] = None,
    priorita: Optional[str] = None,
    categoria: Optional[str] = None,
    due_date: Optional[str] = None,
    client: Optional[Client] = None,
) -> dict:
    """Aggiorna proprieta' arbitrarie di un task. Solo i campi != None vengono toccati.

    Utile per: cambiare priorita, riassegnare categoria, spostare scadenze, rinominare.
    """
    if client is None:
        client = get_client()

    props: dict = {}
    if name is not None:
        props["Name"] = {"title": [{"text": {"content": name[:2000]}}]}
    if status is not None:
        props["Status"] = {"status": {"name": status}}
    if priorita is not None:
        if priorita not in PRIORITA:
            raise ValueError(f"priorita non valida: {priorita}. Validi: {PRIORITA}")
        props["Priorità"] = {"select": {"name": priorita}}
    if categoria is not None:
        if categoria not in CATEGORIE:
            raise ValueError(f"categoria non valida: {categoria}. Validi: {CATEGORIE}")
        props["Categoria"] = {"select": {"name": categoria}}
    if due_date is not None:
        props["Due Date"] = {"date": {"start": due_date}} if due_date else {"date": None}

    if not props:
        raise ValueError("Nessun campo da aggiornare passato")

    return client.pages.update(page_id=page_id, properties=props)


# ─── Lettura task aperti ─────────────────────────────────────────────────────


def _extract_title(prop: dict) -> str:
    """Estrae testo da una property di tipo title."""
    if not prop or prop.get("type") != "title":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def _extract_select(prop: dict) -> Optional[str]:
    """Estrae il name da una property di tipo select o status."""
    if not prop:
        return None
    ptype = prop.get("type")
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if ptype == "status":
        st = prop.get("status")
        return st.get("name") if st else None
    return None


def _extract_date(prop: dict) -> Optional[str]:
    """Estrae la data start (ISO YYYY-MM-DD) da una property di tipo date."""
    if not prop or prop.get("type") != "date":
        return None
    d = prop.get("date")
    return d.get("start") if d else None


def _extract_people_ids(prop: dict) -> list[str]:
    """Estrae la lista user_id da una property di tipo people."""
    if not prop or prop.get("type") != "people":
        return []
    return [p.get("id", "") for p in prop.get("people", []) if p.get("id")]


def _extract_relation_ids(prop: dict) -> list[str]:
    """Estrae la lista page_id da una property di tipo relation."""
    if not prop or prop.get("type") != "relation":
        return []
    return [r.get("id", "") for r in prop.get("relation", []) if r.get("id")]


def _normalize_task(page: dict, lorenzo_user_id: str) -> dict:
    """Normalizza una pagina Notion in un dict piatto facile da consumare."""
    props = page.get("properties", {})
    name = _extract_title(props.get("Name", {}))
    status = _extract_select(props.get("Status", {}))
    priorita = _extract_select(props.get("Priorità", {}))
    categoria = _extract_select(props.get("Categoria", {}))
    due_date = _extract_date(props.get("Due Date", {}))
    assign_ids = _extract_people_ids(props.get("Assign", {}))
    cliente_ids = _extract_relation_ids(props.get("Cliente", {}))

    today = date.today().isoformat()
    due_overdue = bool(due_date and due_date < today)
    assigned_to_lorenzo = lorenzo_user_id in assign_ids

    return {
        "id": page.get("id", ""),
        "url": page.get("url", ""),
        "name": name,
        "status": status,
        "priorita": priorita,
        "categoria": categoria,
        "due_date": due_date,
        "due_overdue": due_overdue,
        "assign_ids": assign_ids,
        "assigned_to_lorenzo": assigned_to_lorenzo,
        "cliente_ids": cliente_ids,
        "created_time": page.get("created_time", ""),
    }


def _build_open_tasks_filter(
    lorenzo_user_id: Optional[str], include_unassigned: bool
) -> dict:
    """Costruisce il filtro JSON per la query Notion."""
    status_filter = {
        "or": [{"property": "Status", "status": {"equals": s}} for s in OPEN_STATUSES]
    }

    if not lorenzo_user_id:
        return status_filter

    assignee_clauses: list[dict] = [
        {"property": "Assign", "people": {"contains": lorenzo_user_id}}
    ]
    if include_unassigned:
        assignee_clauses.append(
            {"property": "Assign", "people": {"is_empty": True}}
        )
    assignee_filter = {"or": assignee_clauses} if len(assignee_clauses) > 1 else assignee_clauses[0]

    return {"and": [status_filter, assignee_filter]}


def list_open_tasks(
    only_lorenzo: bool = True,
    include_unassigned: bool = True,
    page_size: int = 100,
    client: Optional[Client] = None,
) -> list[dict]:
    """Lista i task aperti dal database Tasks_Mailift.

    Filtri applicati:
    - Status ∈ {"To-do", "In corso"}
    - Se only_lorenzo=True: Assign contiene Lorenzo, oppure (se include_unassigned)
      anche i task con Assign vuoto.

    Ritorna una lista di dict normalizzati, ordinata per priorita' (Alta→Bassa)
    poi per due_date asc. Gestisce paginazione con next_cursor.
    """
    if client is None:
        client = get_client()

    data_source_id = os.environ.get("NOTION_TASKS_DATA_SOURCE_ID")
    if not data_source_id:
        raise RuntimeError("NOTION_TASKS_DATA_SOURCE_ID mancante in .env")

    lorenzo_user_id = os.environ.get("NOTION_USER_ID_LORENZO") if only_lorenzo else None
    if only_lorenzo and not lorenzo_user_id:
        raise RuntimeError(
            "NOTION_USER_ID_LORENZO mancante in .env (richiesto se only_lorenzo=True)"
        )

    filter_obj = _build_open_tasks_filter(lorenzo_user_id, include_unassigned)

    results: list[dict] = []
    cursor: Optional[str] = None
    while True:
        kwargs: dict[str, Any] = {
            "data_source_id": data_source_id,
            "filter": filter_obj,
            "page_size": page_size,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.data_sources.query(**kwargs)
        results.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
        if not cursor:
            break

    normalized = [
        _normalize_task(p, lorenzo_user_id or "") for p in results
    ]

    # Sort: priorita' (Alta prima) → due_date asc (None in fondo) → name
    normalized.sort(
        key=lambda t: (
            PRIORITY_RANK.get(t["priorita"], 3),
            t["due_date"] or "9999-99-99",
            t["name"].lower(),
        )
    )
    return normalized


# ─── CLI smoke test ──────────────────────────────────────────────────────────


def _print_summary(tasks: list[dict]) -> None:
    """Stampa un riepilogo human-readable dei task per CLI smoke test."""
    if not tasks:
        print("[notion_tasks] Nessun task aperto trovato.")
        return

    print(f"[notion_tasks] Totale task aperti: {len(tasks)}\n")

    # Breakdown per status
    by_status: dict[str, int] = {}
    by_categoria: dict[str, int] = {}
    by_priorita: dict[str, int] = {}
    overdue_count = 0
    for t in tasks:
        by_status[t["status"] or "?"] = by_status.get(t["status"] or "?", 0) + 1
        by_categoria[t["categoria"] or "(nessuna)"] = (
            by_categoria.get(t["categoria"] or "(nessuna)", 0) + 1
        )
        by_priorita[t["priorita"] or "(nessuna)"] = (
            by_priorita.get(t["priorita"] or "(nessuna)", 0) + 1
        )
        if t["due_overdue"]:
            overdue_count += 1

    print("Breakdown per Status:")
    for k, v in sorted(by_status.items()):
        print(f"  {k:20} {v}")
    print("\nBreakdown per Categoria:")
    for k, v in sorted(by_categoria.items(), key=lambda x: -x[1]):
        print(f"  {k:20} {v}")
    print("\nBreakdown per Priorita:")
    for k in ["Alta", "Media", "Bassa", "(nessuna)"]:
        if k in by_priorita:
            print(f"  {k:20} {by_priorita[k]}")

    if overdue_count:
        print(f"\n⚠️  Task overdue: {overdue_count}")

    print("\nPrime 10 (per priorita + scadenza):")
    for i, t in enumerate(tasks[:10], 1):
        prio = t["priorita"] or "—"
        cat = t["categoria"] or "—"
        due = t["due_date"] or "—"
        overdue_marker = " ⚠️" if t["due_overdue"] else ""
        print(f"  {i:2}. [{prio:5}] [{cat:12}] {due}{overdue_marker}  {t['name']}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        only_lorenzo = "--all" not in sys.argv
        try:
            tasks = list_open_tasks(only_lorenzo=only_lorenzo)
            _print_summary(tasks)
        except Exception as exc:  # noqa: BLE001
            print(f"[notion_tasks] errore: {type(exc).__name__}: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: python tools/notion_tasks.py list [--all]")
        print("  list       elenca task aperti assegnati a Lorenzo (o non assegnati)")
        print("  list --all elenca tutti i task aperti, senza filtro assignee")
        sys.exit(2)
