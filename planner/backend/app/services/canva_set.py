"""Set di template Canva dell'agenzia: elenco di TIPI × varianti.

Il flusso reale di Mailift: un set di template email organizzato per tipo
("About", "Flash Sale", "FAQ", "How-to?", ...) con N varianti ciascuno
(tipicamente 3), mantenuto su Notion come elenco "About x3, Flash Sale x3, ...".

Qui l'elenco viene espanso in righe della tabella `templates` — una per
variante ("About 1", "About 2", "About 3") — con la categoria assegnata
automaticamente dal nome del tipo (mappa keyword → macro-categoria), così il
matching AI per obiettivo email (70/20/10) funziona senza lavoro manuale.

La configurazione (URL file Canva opzionale + elenco tipi) è salvata in
Settings per poterla rileggere e modificare dalla UI.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models.db_models import Template
from .settings_store import get_setting, set_setting

PAGE_ID_PREFIX = "canva-set-"

_URL_KEY = "canva_set_url"
_ENTRIES_KEY = "canva_set_entries"


class CanvaSetInvalid(Exception):
    pass


# Mappa keyword (nel nome del tipo, lowercase) → macro-categoria.
# L'ordine conta: vince la prima keyword trovata.
_CATEGORY_RULES: list[tuple[str, str]] = [
    # promo / offerte
    ("flash sale", "promo"),
    ("bundle", "promo"),
    ("deadline", "promo"),
    ("spend & save", "promo"),
    ("low-stock", "promo"),
    ("gift card", "promo"),
    ("sale", "promo"),
    # lancio / novità
    ("new launch", "lancio prodotto"),
    ("pre-order", "lancio prodotto"),
    ("restock", "lancio prodotto"),
    ("teaser", "lancio prodotto"),
    # focus prodotto (vendita non aggressiva)
    ("product features", "prodotto"),
    ("before & after", "prodotto"),
    ("us vs them", "prodotto"),
    ("problem-solution", "prodotto"),
    ("made with", "prodotto"),
    ("video feature", "prodotto"),
    ("shop by", "prodotto"),
    ("recommendation", "prodotto"),
    ("trending", "prodotto"),
    ("inspo", "prodotto"),
    ("gift guide", "prodotto"),
    # educativo
    ("how-to", "educativo"),
    ("tips", "educativo"),
    ("do's", "educativo"),
    ("dont", "educativo"),
    ("did you know", "educativo"),
    ("facts", "educativo"),
    ("faq", "educativo"),
    ("mythbuster", "educativo"),
    ("statistics", "educativo"),
    ("blog", "educativo"),
    # storytelling
    ("about", "storytelling"),
    # social proof
    ("social proof", "social proof"),
    ("featured in", "social proof"),
    ("social media", "social proof"),
    # engagement / interattive
    ("gamified", "engagement"),
    ("giveaway", "engagement"),
    ("survey", "engagement"),
    ("mystery", "engagement"),
    ("zodiac", "engagement"),
    ("invitation", "engagement"),
    # newsletter / ricorrenti
    ("plain", "newsletter"),
    ("icymi", "newsletter"),
    # stagionale / operativo
    ("special day", "stagionale"),
    ("shipping", "operativo"),
]


def auto_category(type_name: str) -> str:
    low = type_name.lower()
    for keyword, category in _CATEGORY_RULES:
        if keyword in low:
            return category
    return "altro"


_LINE_RE = re.compile(r"^\s*[-•*]?\s*(.+?)\s*(?:[xX×]\s*(\d*))?\s*$")


def parse_entries_text(text: str, default_count: int = 3) -> list[dict]:
    """Parsa l'elenco incollato da Notion: una riga per tipo, "Nome x3".

    Tollerante: bullet, "x" senza numero (usa default_count), righe vuote,
    intestazioni tipo "## Tutte le voci" (scartate).
    """
    entries: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        name = m.group(1).strip(" -•*\t")
        count = int(m.group(2)) if m.group(2) else default_count
        if not name:
            continue
        entries.append({"name": name, "count": count, "category": ""})
    return entries


def get_config(db: Session) -> dict:
    raw = get_setting(db, _ENTRIES_KEY)
    try:
        entries = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        entries = []
    count = (
        db.query(Template)
        .filter(Template.notion_page_id.like(f"{PAGE_ID_PREFIX}%"))
        .count()
    )
    categories = sorted({e.get("category") or auto_category(e["name"]) for e in entries})
    return {
        "canva_file_url": get_setting(db, _URL_KEY),
        "entries": entries,
        "template_count": count,
        "categories": categories,
    }


def _validate(entries: list[dict]) -> list[dict]:
    if not entries:
        raise CanvaSetInvalid(
            "Elenco vuoto: incollare i tipi di template (una riga per tipo, es. 'About x3')."
        )
    cleaned: list[dict] = []
    seen: set[str] = set()
    for e in entries:
        name = str(e.get("name", "")).strip()
        if not name:
            raise CanvaSetInvalid("Ogni voce deve avere un nome.")
        if name.lower() in seen:
            raise CanvaSetInvalid(f"Tipo duplicato nell'elenco: '{name}'.")
        seen.add(name.lower())
        count = e.get("count", 3)
        if not isinstance(count, int) or not 1 <= count <= 50:
            raise CanvaSetInvalid(f"Numero varianti non valido per '{name}' (1-50).")
        category = str(e.get("category", "")).strip().lower() or auto_category(name)
        cleaned.append({"name": name, "count": count, "category": category})
    if sum(e["count"] for e in cleaned) > 1000:
        raise CanvaSetInvalid("Troppi template (max 1000 totali).")
    return cleaned


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tipo"


# ------------------------------------------------------------------ anteprime

PREVIEW_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def previews_dir():
    from ..settings import DATA_DIR

    d = DATA_DIR / "previews"
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_preview_file(page: int):
    d = previews_dir()
    for ext in PREVIEW_EXTS:
        f = d / f"{page}{ext}"
        if f.exists():
            return f
    return None


def _preview_url_if_exists(page: int) -> str:
    return f"/api/templates/previews/{page}" if find_preview_file(page) else ""


def page_of(template: Template) -> int | None:
    """Numero di pagina di un template del set (dal notion_page_id)."""
    m = re.search(r"--(\d+)$", template.notion_page_id or "")
    return int(m.group(1)) if m else None


def save_previews(db: Session, files: list[tuple[str, bytes]]) -> dict:
    """Salva le immagini di anteprima (export PNG del file Canva) e le abbina
    ai template del set per numero di pagina, ricavato dal nome del file
    (Canva esporta '...-12.png' / '12.png').
    """
    import zipfile
    import io

    images: list[tuple[str, bytes]] = []
    for filename, data in files:
        if filename.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for info in zf.infolist():
                    if info.is_dir() or info.file_size > 20 * 1024 * 1024:
                        continue
                    inner = info.filename.rsplit("/", 1)[-1]
                    if inner.lower().endswith(PREVIEW_EXTS) and not inner.startswith("."):
                        images.append((inner, zf.read(info)))
        elif filename.lower().endswith(PREVIEW_EXTS):
            images.append((filename, data))

    saved = 0
    d = previews_dir()
    for filename, data in images:
        numbers = re.findall(r"\d+", filename)
        if not numbers:
            continue
        page = int(numbers[-1])  # Canva numera in coda: "Design - 12.png"
        if not 1 <= page <= 2000:
            continue
        ext = "." + filename.rsplit(".", 1)[-1].lower()
        for old_ext in PREVIEW_EXTS:  # una sola anteprima per pagina
            old = d / f"{page}{old_ext}"
            if old.exists():
                old.unlink()
        (d / f"{page}{ext}").write_bytes(data)
        saved += 1

    # aggiorna i preview_url dei template del set
    matched = 0
    for t in db.query(Template).filter(
        Template.notion_page_id.like(f"{PAGE_ID_PREFIX}%")
    ):
        page = page_of(t)
        if page is None:
            continue
        t.preview_url = _preview_url_if_exists(page)
        if t.preview_url:
            matched += 1
    db.commit()
    return {"saved": saved, "matched": matched}


def apply_set(db: Session, canva_file_url: str, entries: list[dict]) -> dict:
    """Valida, salva la configurazione e rigenera la libreria template.

    Sostituisce l'intera tabella templates (come la sync da Notion): la
    libreria ha una sola sorgente attiva alla volta.
    """
    cleaned = _validate(entries)
    url = canva_file_url.strip()

    set_setting(db, _URL_KEY, url)
    set_setting(db, _ENTRIES_KEY, json.dumps(cleaned, ensure_ascii=False))

    now = datetime.now(timezone.utc)
    db.query(Template).delete()
    created = 0
    page = 0  # pagina globale nel file Canva: segue l'ordine dell'elenco
    for e in cleaned:
        slug = _slug(e["name"])
        for n in range(1, e["count"] + 1):
            page += 1
            db.add(
                Template(
                    # il numero di pagina in coda permette il match con le anteprime
                    notion_page_id=f"{PAGE_ID_PREFIX}{slug}--{page}",
                    name=f"{e['name']} {n}" if e["count"] > 1 else e["name"],
                    category=e["category"],
                    # l'ancora #N apre il file Canva direttamente sulla pagina giusta
                    canva_url=f"{url}#{page}" if url else "",
                    notion_url="",
                    tags=[e["name"], f"pagina {page}"],
                    preview_url=_preview_url_if_exists(page),
                    last_synced_at=now,
                )
            )
            created += 1
    db.commit()

    return {
        "canva_file_url": url,
        "entries": cleaned,
        "template_count": created,
        "categories": sorted({e["category"] for e in cleaned}),
    }
