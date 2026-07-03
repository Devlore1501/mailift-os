"""Set di template Canva "a file unico".

Il flusso reale dell'agenzia: UN solo file Canva editabile con i template
numerati (una pagina per template) e una categorizzazione per intervalli di
numeri (es. 1-5 promo, 7-21 educative), mantenuta su Notion come documento.

Qui l'intervallo viene espanso in righe della tabella `templates` — una per
numero ("Template 3", categoria promo, link al file Canva) — così tutto il
resto della pipeline (catalogo passato a Claude, matching per categoria,
card email, pubblicazione Notion) funziona senza cambiare nulla.

La configurazione (URL file + intervalli) è salvata in Settings per poterla
rileggere e modificare dalla UI.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.db_models import Template
from .settings_store import get_setting, set_setting

PAGE_ID_PREFIX = "canva-set-"

_URL_KEY = "canva_set_url"
_RANGES_KEY = "canva_set_ranges"


class CanvaSetInvalid(Exception):
    pass


def get_config(db: Session) -> dict:
    """Configurazione corrente del set + quanti template ha generato."""
    raw = get_setting(db, _RANGES_KEY)
    try:
        ranges = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        ranges = []
    count = (
        db.query(Template)
        .filter(Template.notion_page_id.like(f"{PAGE_ID_PREFIX}%"))
        .count()
    )
    return {
        "canva_file_url": get_setting(db, _URL_KEY),
        "ranges": ranges,
        "template_count": count,
    }


def _validate(canva_file_url: str, ranges: list[dict]) -> list[dict]:
    if not canva_file_url.strip():
        raise CanvaSetInvalid("Indicare l'URL del file Canva con i template.")
    if not ranges:
        raise CanvaSetInvalid("Indicare almeno un intervallo (categoria, da, a).")

    cleaned: list[dict] = []
    for r in ranges:
        category = str(r.get("category", "")).strip().lower()
        start, end = r.get("start"), r.get("end")
        if not category:
            raise CanvaSetInvalid("Ogni intervallo deve avere una categoria.")
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise CanvaSetInvalid(
                f"Intervallo non valido per '{category}': servono numeri con 1 ≤ da ≤ a."
            )
        cleaned.append({"category": category, "start": start, "end": end})

    cleaned.sort(key=lambda r: r["start"])
    for prev, cur in zip(cleaned, cleaned[1:]):
        if cur["start"] <= prev["end"]:
            raise CanvaSetInvalid(
                f"Gli intervalli '{prev['category']}' ({prev['start']}-{prev['end']}) e "
                f"'{cur['category']}' ({cur['start']}-{cur['end']}) si sovrappongono."
            )
    return cleaned


def apply_set(db: Session, canva_file_url: str, ranges: list[dict]) -> dict:
    """Valida, salva la configurazione e rigenera la libreria template.

    Sostituisce l'intera tabella templates (come la sync da Notion): la
    libreria ha una sola sorgente attiva alla volta.
    """
    cleaned = _validate(canva_file_url, ranges)
    url = canva_file_url.strip()

    set_setting(db, _URL_KEY, url)
    set_setting(db, _RANGES_KEY, json.dumps(cleaned, ensure_ascii=False))

    now = datetime.now(timezone.utc)
    db.query(Template).delete()
    created = 0
    for r in cleaned:
        for n in range(r["start"], r["end"] + 1):
            db.add(
                Template(
                    notion_page_id=f"{PAGE_ID_PREFIX}{n:04d}",
                    name=f"Template {n}",
                    category=r["category"],
                    canva_url=url,
                    notion_url="",
                    tags=[f"n.{n}"],
                    last_synced_at=now,
                )
            )
            created += 1
    db.commit()

    return {
        "canva_file_url": url,
        "ranges": cleaned,
        "template_count": created,
    }
