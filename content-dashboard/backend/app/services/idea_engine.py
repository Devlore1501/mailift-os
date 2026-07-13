"""M3 Idea Engine: fetch fonti (RSS/Reddit/trend), dedup, sintesi AI → coda review.

- Il fetch fallisce con grazia per singola fonte (NFR-08): l'errore finisce in
  source.last_error, le altre fonti proseguono.
- All'LLM vanno solo titolo+snippet degli item pubblici, nessun dato personale (NFR-07).
- Human-in-the-loop: le proposte nascono status=proposed, l'umano approva/edita/scarta.
"""
import json
import logging
import os

import feedparser
import requests
from sqlalchemy.orm import Session

from ..enums import FORMATS, PILLARS
from ..models import Idea, Source, SourceItem, utcnow
from ..settings import ANTHROPIC_API_KEY, ANTHROPIC_MODEL

log = logging.getLogger("idea_engine")

MAX_ITEMS_PER_FETCH = 25
MAX_ITEMS_PER_SYNTHESIS = 20
FETCH_TIMEOUT_SECONDS = 20
# User agent identificabile: rispetto dei ToS delle fonti (NFR-06)
FETCH_USER_AGENT = "MailiftContentDashboard/1.0 (idea engine interno; contatto: mailift.it)"


def _fetch_feed(url: str):
    """Scarica il feed via requests (rispetta HTTPS_PROXY/CA bundle) e lo passa a feedparser.

    I path locali restano supportati (usati nei test).
    """
    if not url.startswith(("http://", "https://")):
        if not os.path.exists(url):
            raise ValueError(f"path feed inesistente: {url}")
        return feedparser.parse(url)
    response = requests.get(
        url, timeout=FETCH_TIMEOUT_SECONDS, headers={"User-Agent": FETCH_USER_AGENT},
    )
    response.raise_for_status()
    return feedparser.parse(response.content)

PROPOSAL_TOOL = {
    "name": "submit_proposals",
    "description": "Registra le proposte di contenuto generate dagli item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "proposals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_item_id": {"type": "integer"},
                        "title": {"type": "string", "description": "Titolo breve dell'idea"},
                        "angle": {"type": "string", "description": "Angolo per owner eCommerce DTC"},
                        "pillar": {"type": "string", "enum": list(PILLARS)},
                        "format": {"type": "string", "enum": list(FORMATS)},
                        "hook_draft": {"type": "string", "description": "Bozza hook (prime 3s)"},
                        "relevance": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["source_item_id", "title", "angle", "pillar", "relevance"],
                },
            }
        },
        "required": ["proposals"],
    },
}

SYSTEM_PROMPT = """Sei l'Idea Engine di Mailift, agenzia italiana di email marketing per eCommerce DTC (Shopify + Klaviyo).
Generi proposte di contenuti organici (TikTok/IG Reels, caroselli, story) a partire da notizie e discussioni.

Contesto strategico:
- ICP: owner di eCommerce DTC italiani €25k-300k/mese. NON freelance, NON agenzie.
- Obiettivo: attirare owner verso il Flow Health Score (€37) e i retainer. Le idee devono parlare di soldi persi, revenue nascosta, email marketing, retention clienti.
- Pillar: revenue_leak (soldi che l'eCommerce sta perdendo), proof (risultati/case study), educational (come fare), contrarian (contro il senso comune del settore), backstage (dietro le quinte agenzia).

Regole:
- Proponi SOLO idee rilevanti per owner eCommerce; scarta item fuori tema (non generare proposte per quelli).
- relevance 1-10: quanto l'idea può attirare l'ICP (10 = perfetta per owner eCommerce italiani).
- hook_draft in italiano, diretto, senza clickbait vuoto.
- Massimo una proposta per item; se un item non è rilevante, semplicemente non proporlo."""


def fetch_sources(db: Session, source_ids: list[int] | None = None) -> dict:
    """Fetch di tutte le fonti attive (o del sottoinsieme indicato), con dedup per URL."""
    q = db.query(Source).filter(Source.active.is_(True))
    if source_ids:
        q = q.filter(Source.id.in_(source_ids))
    sources = q.all()

    results = []
    for source in sources:
        added, error = 0, None
        try:
            feed = _fetch_feed(source.url)
            if feed.bozo and not feed.entries:
                raise ValueError(f"feed non leggibile: {getattr(feed, 'bozo_exception', 'parse error')}")
            existing = {
                url for (url,) in db.query(SourceItem.url)
                .filter(SourceItem.source_id == source.id).all()
            }
            for entry in feed.entries[:MAX_ITEMS_PER_FETCH]:
                url = entry.get("link") or entry.get("id")
                title = (entry.get("title") or "").strip()
                if not url or not title or url in existing:
                    continue
                snippet = (entry.get("summary") or entry.get("description") or "")[:1000]
                db.add(SourceItem(
                    source_id=source.id, title=title[:500], url=url, snippet=snippet,
                    raw=json.dumps({k: str(entry.get(k)) for k in ("published", "author")}),
                ))
                existing.add(url)
                added += 1
            source.last_fetched_at = utcnow()
            source.last_error = None
        except Exception as exc:  # noqa: BLE001 — una fonte down non blocca le altre (NFR-08)
            error = str(exc)[:500]
            source.last_error = error
            log.warning("fetch fonte %s (%s) fallito: %s", source.id, source.label, error)
        results.append({"source_id": source.id, "label": source.label, "added": added, "error": error})
    db.commit()
    return {"sources": results, "total_added": sum(r["added"] for r in results)}


def synthesize_proposals(db: Session) -> dict:
    """Genera proposte AI dagli item non ancora processati (FR-M3-03)."""
    items = (
        db.query(SourceItem)
        .filter(SourceItem.processed.is_(False))
        .order_by(SourceItem.fetched_at.desc())
        .limit(MAX_ITEMS_PER_SYNTHESIS)
        .all()
    )
    if not items:
        return {"proposals_created": 0, "items_processed": 0, "detail": "nessun item nuovo"}
    if not ANTHROPIC_API_KEY:
        return {
            "proposals_created": 0, "items_processed": 0,
            "error": "ANTHROPIC_API_KEY mancante nel .env: la sintesi AI è disattivata. "
                     "Gli item restano in coda e verranno processati appena la chiave è configurata.",
        }

    import anthropic

    payload = [
        {"id": it.id, "title": it.title, "snippet": (it.snippet or "")[:600]}
        for it in items
    ]
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[PROPOSAL_TOOL],
        tool_choice={"type": "tool", "name": "submit_proposals"},
        messages=[{
            "role": "user",
            "content": "Item raccolti dalle fonti:\n" + json.dumps(payload, ensure_ascii=False, indent=1),
        }],
    )
    proposals = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_proposals":
            proposals = block.input.get("proposals", [])

    valid_ids = {it.id for it in items}
    created = 0
    for p in proposals:
        if p.get("source_item_id") not in valid_ids:
            continue
        pillar = p.get("pillar") if p.get("pillar") in PILLARS else None
        fmt = p.get("format") if p.get("format") in FORMATS else None
        relevance = max(1, min(10, int(p.get("relevance", 5))))
        db.add(Idea(
            title=p["title"][:300],
            angle=p.get("angle"),
            pillar=pillar,
            status="proposed",
            origin="ai",
            source_item_id=p["source_item_id"],
            relevance_score=relevance,
            hook_draft=p.get("hook_draft"),
            suggested_format=fmt,
        ))
        created += 1
    for it in items:
        it.processed = True
    db.commit()
    return {"proposals_created": created, "items_processed": len(items)}


EVERGREEN_TOOL = {
    "name": "submit_evergreen_ideas",
    "description": "Registra spunti di contenuto evergreen (non legati a notizie).",
    "input_schema": {
        "type": "object",
        "properties": {
            "ideas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "angle": {"type": "string"},
                        "pillar": {"type": "string", "enum": list(PILLARS)},
                        "format": {"type": "string", "enum": list(FORMATS)},
                        "hook_draft": {"type": "string"},
                        "relevance": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["title", "angle", "pillar", "relevance"],
                },
            }
        },
        "required": ["ideas"],
    },
}

EVERGREEN_PROMPT = """Genera {n} spunti di contenuto EVERGREEN per Mailift: argomenti interessanti da trattare
che non dipendono da notizie del giorno. Temi da cui pescare (non limitarti a questi):
- soldi che un eCommerce perde senza saperlo (carrelli, winback, post-purchase, segmentazione)
- errori tipici degli owner con Klaviyo/Shopify e come evitarli
- miti da sfatare su email marketing, sconti, pop-up, open rate
- confronti controintuitivi (email vs ads, sconto vs valore, lista grande vs lista pulita)
- casi e numeri concreti che parlano a store da 25k-300k€/mese
- dietro le quinte di come lavora un'agenzia email

Vincoli:
- Bilancia i pillar rispettando all'incirca il mix: revenue_leak 30%, proof 25%, educational 25%, contrarian 10%, backstage 10%.
- NON ripetere idee già in lavorazione. Titoli già usati:
{existing}
- Titoli e hook in italiano, concreti, rivolti a owner di eCommerce (mai a freelance o agenzie)."""


def generate_evergreen(db: Session, n: int = 6) -> dict:
    """Spunti evergreen proposti dall'AI, in coda review come le proposte da fonti."""
    if not ANTHROPIC_API_KEY:
        return {
            "proposals_created": 0,
            "error": "ANTHROPIC_API_KEY mancante nel .env: la generazione di spunti è disattivata.",
        }

    import anthropic

    recent_titles = [
        title for (title,) in
        db.query(Idea.title).order_by(Idea.created_at.desc()).limit(40).all()
    ]
    existing = "\n".join(f"- {t}" for t in recent_titles) or "- (nessuna)"
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[EVERGREEN_TOOL],
        tool_choice={"type": "tool", "name": "submit_evergreen_ideas"},
        messages=[{"role": "user", "content": EVERGREEN_PROMPT.format(n=n, existing=existing)}],
    )
    ideas = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_evergreen_ideas":
            ideas = block.input.get("ideas", [])

    seen = {t.strip().lower() for t in recent_titles}
    created = 0
    for p in ideas[: n * 2]:
        title = (p.get("title") or "").strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        db.add(Idea(
            title=title[:300],
            angle=p.get("angle"),
            pillar=p.get("pillar") if p.get("pillar") in PILLARS else None,
            status="proposed",
            origin="ai",
            relevance_score=max(1, min(10, int(p.get("relevance", 5)))),
            hook_draft=p.get("hook_draft"),
            suggested_format=p.get("format") if p.get("format") in FORMATS else None,
        ))
        created += 1
    db.commit()
    return {"proposals_created": created}


SCRIPT_TOOL = {
    "name": "submit_script",
    "description": "Registra la bozza di script generata per il contenuto.",
    "input_schema": {
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "Bozza completa dello script in italiano"},
            "hook": {"type": "string", "description": "Hook (prime 3 secondi), solo se non già fornito"},
            "cta_keyword": {"type": "string", "description": "Keyword DM suggerita (una parola), solo se non già fornita"},
        },
        "required": ["script"],
    },
}

SURFACE_SCRIPT_GUIDE = {
    "reel": "Reel 30-45 secondi (~110-150 parole parlate). Struttura: HOOK (3s) → problema concreto in euro → 2-3 punti/passaggi → CTA finale con keyword da commentare in DM. Indica tra [parentesi] le indicazioni visive essenziali.",
    "carousel": "Carosello 6-8 slide. Formato: SLIDE 1: gancio forte · SLIDE 2: il problema quantificato · SLIDE 3-6: un punto per slide, testo breve · ULTIMA SLIDE: CTA con keyword DM. Max 25 parole per slide.",
    "story": "Sequenza di 3-5 story. Formato: STORY 1: gancio + sondaggio/domanda · STORY 2-3: sviluppo rapido · ULTIMA: CTA con link/keyword. Tono diretto, da parlato.",
    "other": "Formato libero ma breve: hook, corpo in 2-3 punti, CTA con keyword DM.",
}


def generate_script(content, idea=None) -> dict:
    """Bozza script AI per un contenuto (hook/pillar/format come brief). Human-in-the-loop:
    la bozza va nel campo script della UI, l'umano la rifinisce e salva."""
    if not ANTHROPIC_API_KEY:
        return {"error": "ANTHROPIC_API_KEY mancante nel .env: la generazione script è disattivata."}

    import anthropic

    brief = {
        "titolo": content.title or (idea.title if idea else None),
        "idea_madre": idea.title if idea else None,
        "angolo": idea.angle if idea else None,
        "pillar": PILLARS.get(content.pillar, content.pillar),
        "surface": content.surface,
        "format": FORMATS.get(content.format, content.format),
        "hook_esistente": content.hook,
        "cta_keyword_esistente": content.cta_keyword,
        "note_di_regia": content.notes,
    }
    guide = SURFACE_SCRIPT_GUIDE.get(content.surface, SURFACE_SCRIPT_GUIDE["other"])
    prompt = (
        "Scrivi la bozza di script per questo contenuto organico di Mailift.\n\n"
        f"Brief:\n{json.dumps({k: v for k, v in brief.items() if v}, ensure_ascii=False, indent=1)}\n\n"
        f"Formato richiesto: {guide}\n\n"
        "Regole:\n"
        "- Parla a owner di eCommerce DTC italiani (mai a freelance/agenzie); usa numeri ed euro concreti.\n"
        "- Se c'è un hook esistente, aprilo con quello (puoi limarlo); altrimenti proponine uno.\n"
        "- CTA coerente col funnel Mailift: commenta/scrivi la keyword in DM per ricevere il Flow Health Score.\n"
        "- Niente gergo da marketer, niente promesse gonfiate. Tono diretto, primo persona singolare."
    )
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[SCRIPT_TOOL],
        tool_choice={"type": "tool", "name": "submit_script"},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_script":
            return {
                "script": block.input.get("script", ""),
                "hook": block.input.get("hook"),
                "cta_keyword": block.input.get("cta_keyword"),
            }
    return {"error": "L'AI non ha restituito uno script: riprova."}


def run_job(db: Session) -> dict:
    """Job completo (FR-M3-02): fetch + sintesi. Usato dallo scheduler e dal trigger manuale."""
    fetch_result = fetch_sources(db)
    synth_result = synthesize_proposals(db)
    return {"fetch": fetch_result, "synthesis": synth_result}
