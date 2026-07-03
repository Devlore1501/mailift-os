"""Integrazione Notion: lettura database template Canva + pubblicazione calendario.

- sync_templates: legge il DB Notion (~350 template categorizzati) e aggiorna la
  cache locale (tabella templates). Mappa le proprietà in modo tollerante:
  title → name, select/multi_select "categoria/category/tipo/type" → category,
  url (o rich_text con link) contenente "canva"/"link"/"url" → canva_url,
  multi_select "tag/tags" → tags.
- publish_plan: crea un database Notion sotto la pagina calendario con una riga
  per email (giorno, oggetto, segmento, template, stato) e il testo completo
  nel corpo della pagina.

Se Notion non è configurato: sync_templates in mock_mode seeda template demo;
publish_plan in mock_mode simula URL finti. Altrimenti solleva NotionNotConfigured.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .. import settings as cfg
from ..models.db_models import Template
from . import mockdata
from .settings_store import notion_config


class NotionNotConfigured(Exception):
    pass


class NotionAPIError(Exception):
    pass


def _client(token: str):
    from notion_client import Client

    return Client(auth=token)


# ---------------------------------------------------------------- templates


def _extract_template(page: dict) -> dict | None:
    props: dict[str, Any] = page.get("properties", {})
    name = ""
    category = ""
    canva_url = ""
    tags: list[str] = []

    for key, prop in props.items():
        ptype = prop.get("type")
        lkey = key.lower()
        if ptype == "title":
            name = "".join(t.get("plain_text", "") for t in prop.get("title", []))
        elif ptype in ("select", "status") and prop.get(ptype):
            if any(k in lkey for k in ("categ", "tipo", "type")) or not category:
                category = (prop[ptype] or {}).get("name", "") or category
        elif ptype == "multi_select":
            values = [v.get("name", "") for v in prop.get("multi_select", [])]
            if any(k in lkey for k in ("tag",)):
                tags = values
            elif any(k in lkey for k in ("categ", "tipo", "type")) and values:
                category = values[0]
            elif not tags:
                tags = values
        elif ptype == "url" and prop.get("url"):
            if "canva" in (prop["url"] or "").lower() or not canva_url:
                canva_url = prop["url"]
        elif ptype == "rich_text":
            for t in prop.get("rich_text", []):
                href = t.get("href")
                if href and ("canva" in href.lower() or not canva_url):
                    canva_url = href

    if not name:
        return None
    return {
        "notion_page_id": page.get("id", ""),
        "name": name,
        "category": category.lower().strip(),
        "canva_url": canva_url,
        "notion_url": page.get("url", ""),
        "tags": tags,
    }


def sync_templates(db: Session) -> dict:
    conf = notion_config(db)
    rows: list[dict]

    if conf["token"] and conf["templates_db_id"]:
        client = _client(conf["token"])
        rows = []
        cursor = None
        try:
            while True:
                resp = client.databases.query(
                    database_id=conf["templates_db_id"],
                    start_cursor=cursor,
                    page_size=100,
                )
                for page in resp.get("results", []):
                    row = _extract_template(page)
                    if row:
                        rows.append(row)
                if not resp.get("has_more"):
                    break
                cursor = resp.get("next_cursor")
        except Exception as e:  # notion_client APIResponseError o rete
            raise NotionAPIError(f"Errore lettura database Notion: {e}") from e
    elif cfg.mock_mode() or not conf["token"]:
        rows = mockdata.mock_template_rows()
    else:
        raise NotionNotConfigured("Configurare token Notion e templates_db_id in Impostazioni.")

    now = datetime.now(timezone.utc)
    existing = {t.notion_page_id: t for t in db.query(Template).all()}
    seen = set()
    for row in rows:
        seen.add(row["notion_page_id"])
        t = existing.get(row["notion_page_id"])
        if t is None:
            t = Template(notion_page_id=row["notion_page_id"])
            db.add(t)
        t.name = row["name"]
        t.category = row["category"]
        t.canva_url = row["canva_url"]
        t.notion_url = row["notion_url"]
        t.tags = row["tags"]
        t.last_synced_at = now
    for page_id, t in existing.items():
        if page_id not in seen:
            db.delete(t)
    db.commit()

    categories = {t.category for t in db.query(Template).all() if t.category}
    return {"synced": len(rows), "categories": len(categories)}


# ---------------------------------------------------------------- publish

_STATUS_IT = {"draft": "Bozza", "edited": "Bozza", "approved": "Approvata"}


def _email_page_properties(email: dict, subject: str) -> dict:
    props: dict[str, Any] = {
        "Email": {"title": [{"text": {"content": subject[:200] or f"Email {email['position']}"}}]},
        "Data": {"date": {"start": email["send_date"]}} if email.get("send_date") else None,
        "Orario": {"rich_text": [{"text": {"content": email.get("send_time", "")}}]},
        "Obiettivo": {"select": {"name": email.get("objective", "nurturing")}},
        "Formato": {"select": {"name": email.get("format", "grafica")}},
        "Sequenza": {
            "rich_text": [
                {
                    "text": {
                        "content": (
                            f"{email['campaign'].get('name', '')} · {email['campaign'].get('role', '')}"
                            if email.get("campaign")
                            else ""
                        )[:200]
                    }
                }
            ]
        },
        "Segmento": {
            "rich_text": [{"text": {"content": (email.get("segment") or {}).get("name", "")[:200]}}]
        },
        "Preview": {"rich_text": [{"text": {"content": email.get("preview_text", "")[:200]}}]},
        "Stato": {"select": {"name": _STATUS_IT.get(email.get("status", "draft"), "Bozza")}},
    }
    tpl = email.get("canva_template") or {}
    if tpl.get("canva_url"):
        props["Template Canva"] = {"url": tpl["canva_url"]}
    return {k: v for k, v in props.items() if v is not None}


def _body_blocks(email: dict) -> list[dict]:
    blocks: list[dict] = []

    def heading(text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [{"text": {"content": text}}]},
        }

    def para(text: str) -> dict:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": text[:1990]}}]},
        }

    blocks.append(heading("Tema e angolo"))
    blocks.append(para(f"{email.get('theme', '')} — {email.get('angle', '')}"))
    seg = email.get("segment") or {}
    blocks.append(heading("Segmento"))
    blocks.append(para(f"{seg.get('name', '')} — {seg.get('rationale', '')}"))
    blocks.append(heading("Oggetti (A/B)"))
    for s in email.get("subject_variants", []):
        blocks.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": s[:200]}}]},
            }
        )
    copy_blocks = email.get("blocks") or []
    if copy_blocks:
        _LABEL = {
            "banner": "Banner principale",
            "sezione": "Sezione",
            "info": "Info",
            "cta_finale": "CTA finale",
        }
        blocks.append(heading("Scaletta per il designer"))
        for cb in copy_blocks:
            blocks.append(heading(_LABEL.get(cb.get("type", ""), cb.get("type", "Blocco"))))
            for label, key in (
                ("Headline", "headline"),
                ("Sub-headline", "subheadline"),
                ("Testo", "text"),
                ("CTA", "cta"),
                ("Visual", "visual"),
            ):
                value = (cb.get(key) or "").strip()
                if value:
                    blocks.append(para(f"{label}: {value}"))
    else:
        blocks.append(heading("Testo email"))
        body = email.get("body", "")
        for chunk in [body[i : i + 1900] for i in range(0, len(body), 1900)] or [""]:
            blocks.append(para(chunk))
    tpl = email.get("canva_template") or {}
    if tpl.get("name"):
        blocks.append(heading("Template Canva"))
        blocks.append(para(f"{tpl['name']} ({tpl.get('category', '')}) — {tpl.get('canva_url', '')}"))
    return blocks


def publish_plan(db: Session, brand_name: str, month_start: str, emails: list[dict]) -> dict:
    conf = notion_config(db)

    if not conf["token"] or not conf["calendar_parent_page_id"]:
        if cfg.mock_mode():
            return {
                "notion_database_id": "mock-db-id",
                "notion_url": "https://www.notion.so/mock-calendario-editoriale",
                "pages": [
                    {
                        "email_id": e["id"],
                        "notion_url": f"https://www.notion.so/mock-email-{e['id']}",
                    }
                    for e in emails
                ],
            }
        raise NotionNotConfigured(
            "Configurare token Notion e calendar_parent_page_id in Impostazioni."
        )

    client = _client(conf["token"])
    try:
        database = client.databases.create(
            parent={"type": "page_id", "page_id": conf["calendar_parent_page_id"]},
            title=[
                {
                    "type": "text",
                    "text": {"content": f"Calendario editoriale {brand_name} — mese {month_start[:7]}"},
                }
            ],
            properties={
                "Email": {"title": {}},
                "Data": {"date": {}},
                "Orario": {"rich_text": {}},
                "Obiettivo": {
                    "select": {
                        "options": [
                            {"name": "nurturing", "color": "blue"},
                            {"name": "promo", "color": "yellow"},
                            {"name": "storytelling", "color": "purple"},
                            {"name": "vendita", "color": "green"},
                        ]
                    }
                },
                "Formato": {
                    "select": {
                        "options": [
                            {"name": "grafica", "color": "pink"},
                            {"name": "testuale", "color": "default"},
                        ]
                    }
                },
                "Sequenza": {"rich_text": {}},
                "Segmento": {"rich_text": {}},
                "Preview": {"rich_text": {}},
                "Template Canva": {"url": {}},
                "Stato": {
                    "select": {
                        "options": [
                            {"name": "Bozza", "color": "gray"},
                            {"name": "Approvata", "color": "green"},
                            {"name": "Programmata", "color": "blue"},
                            {"name": "Inviata", "color": "purple"},
                        ]
                    }
                },
            },
        )
        pages = []
        for email in emails:
            subject = (email.get("subject_variants") or [""])[0]
            page = client.pages.create(
                parent={"type": "database_id", "database_id": database["id"]},
                properties=_email_page_properties(email, subject),
                children=_body_blocks(email),
            )
            pages.append({"email_id": email["id"], "notion_url": page.get("url", "")})
        return {
            "notion_database_id": database["id"],
            "notion_url": database.get("url", ""),
            "pages": pages,
        }
    except (NotionNotConfigured, NotionAPIError):
        raise
    except Exception as e:
        raise NotionAPIError(f"Errore pubblicazione su Notion: {e}") from e
