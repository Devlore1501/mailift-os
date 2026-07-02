"""Generazione piani e copy email via API Claude (structured output).

In mock_mode (nessuna ANTHROPIC_API_KEY) delega a mockdata per piani demo.
"""

from __future__ import annotations

import json
from typing import Any

from .. import settings as cfg
from . import mockdata

_EMAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "position": {"type": "integer"},
        "send_date": {"type": "string", "description": "Data invio ISO YYYY-MM-DD"},
        "send_day": {"type": "string", "description": "Giorno in italiano, es. martedì"},
        "send_time": {"type": "string", "description": "Orario HH:MM"},
        "objective": {
            "type": "string",
            "enum": ["nurturing", "promo", "storytelling", "vendita"],
        },
        "theme": {"type": "string"},
        "angle": {"type": "string"},
        "segment": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "klaviyo_segment_id": {"type": ["string", "null"]},
                "rationale": {"type": "string"},
            },
            "required": ["name", "klaviyo_segment_id", "rationale"],
            "additionalProperties": False,
        },
        "subject_variants": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-3 varianti oggetto per A/B test",
        },
        "preview_text": {"type": "string"},
        "body": {
            "type": "string",
            "description": "Testo email completo: hook, corpo, CTA. Markdown leggero.",
        },
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["name", "reason"],
                "additionalProperties": False,
            },
        },
        "offer": {
            "type": ["object", "null"],
            "properties": {
                "name": {"type": "string"},
                "code": {"type": "string"},
                "discount": {"type": "string"},
            },
            "required": ["name", "code", "discount"],
            "additionalProperties": False,
        },
        "template_notion_page_id": {
            "type": ["string", "null"],
            "description": "notion_page_id del template Canva più adatto, dal catalogo fornito",
        },
    },
    "required": [
        "position",
        "send_date",
        "send_day",
        "send_time",
        "objective",
        "theme",
        "angle",
        "segment",
        "subject_variants",
        "preview_text",
        "body",
        "products",
        "offer",
        "template_notion_page_id",
    ],
    "additionalProperties": False,
}

_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"emails": {"type": "array", "items": _EMAIL_SCHEMA}},
    "required": ["emails"],
    "additionalProperties": False,
}

_SYSTEM = """Sei un email marketing strategist senior specializzato in eCommerce DTC su Klaviyo.
Lavori per un'agenzia italiana e produci piani editoriali email settimanali pronti da eseguire.

Regole non negoziabili:
- Scrivi SEMPRE in italiano, nel tono di voce del brand e nel linguaggio del suo avatar.
- Regola 80/20: la maggioranza delle email deve essere contenuto (nurturing/storytelling), \
massimo ~20-40% promo/vendita. Con 3 email: al più 1 promo. Con 4-5: al più 2.
- Scegli i segmenti in base ai DATI Klaviyo forniti: se l'engagement è basso ("poor"), \
restringi gli invii ai segmenti engaged e includi una email di re-engagement verso gli inattivi. \
Se non ci sono dati, proponi segmenti standard e spiegalo nel rationale.
- Ogni corpo email è completo e pronto all'uso: hook forte nelle prime 2 righe, corpo che \
sviluppa UN solo angolo, una CTA chiara. Usa {{ first_name|default:'' }} come merge tag Klaviyo \
se serve personalizzazione. Lunghezza 120-250 parole.
- Oggetti: 2-3 varianti brevi (max ~45 caratteri), curiosità o beneficio, mai clickbait vuoto.
- Per ogni email scegli dal catalogo template fornito il template Canva più adatto al tipo di \
email e ritorna il suo notion_page_id (null solo se il catalogo è vuoto).
- Distribuisci gli invii nella settimana (mai due email nello stesso giorno), orari mattina \
8:30-10:00 nei feriali; il weekend va bene 9:30-11:00. Se le performance passate suggeriscono \
altro, adeguati.
- Usa solo prodotti e offerte realmente forniti; non inventare sconti o codici."""


def _fmt_context(context: dict) -> str:
    """Serializza il contesto brand in un blocco leggibile per il prompt."""
    brand = context["brand"]
    parts = [
        "## Brand",
        f"Nome: {brand['name']}",
        f"Descrizione: {brand.get('description') or '-'}",
        f"Tono di voce: {brand.get('tone_of_voice') or '-'}",
        f"Mission: {brand.get('mission') or '-'}",
        f"Posizionamento: {brand.get('positioning') or '-'}",
        f"Avatar/buyer persona: {json.dumps(brand.get('avatar') or {}, ensure_ascii=False)}",
        "",
        "## Catalogo prodotti",
        json.dumps(context.get("products", []), ensure_ascii=False, indent=1) or "[]",
        "",
        "## Offerte e codici sconto attivi",
        json.dumps(context.get("offers", []), ensure_ascii=False, indent=1) or "[]",
        "",
        "## Occasioni/temi del periodo",
        json.dumps(context.get("occasions", []), ensure_ascii=False, indent=1) or "[]",
        "",
        "## Dati Klaviyo (segmenti reali, performance campagne, salute lista)",
        json.dumps(context.get("klaviyo") or {"nota": "nessun dato sincronizzato"},
                   ensure_ascii=False, indent=1),
        "",
        "## Catalogo template Canva disponibili (scegli per notion_page_id)",
        json.dumps(
            [
                {
                    "notion_page_id": t["notion_page_id"],
                    "name": t["name"],
                    "category": t["category"],
                    "tags": t.get("tags", []),
                }
                for t in context.get("templates", [])[:250]
            ],
            ensure_ascii=False,
        ),
    ]
    return "\n".join(parts)


def _call_claude(system: str, user: str, schema: dict, max_tokens: int = 32000) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    with client.messages.stream(
        model=cfg.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        raise RuntimeError("La generazione è stata rifiutata dal modello (refusal).")
    text = next((b.text for b in message.content if b.type == "text"), "")
    return json.loads(text)


def generate_plan(context: dict) -> dict:
    """Ritorna {"emails": [...]} secondo _PLAN_SCHEMA."""
    if cfg.mock_mode():
        return mockdata.mock_plan(context)

    user = (
        f"Genera il piano editoriale email per la settimana che inizia lunedì "
        f"{context['week_start']}. Numero email richieste: {context['num_emails']}.\n"
        + (f"Indicazioni extra dell'utente: {context['notes']}\n" if context.get("notes") else "")
        + "\n"
        + _fmt_context(context)
    )
    plan = _call_claude(_SYSTEM, user, _PLAN_SCHEMA)
    emails = plan.get("emails", [])
    # normalizza le position
    for i, e in enumerate(emails, start=1):
        e["position"] = i
    return {"emails": emails}


def regenerate_email(context: dict, current_email: dict, instructions: str) -> dict:
    """Rigenera una singola email del piano mantenendo coerenza col resto."""
    if cfg.mock_mode():
        return mockdata.mock_regenerated_email(current_email, instructions)

    user = (
        "Rigenera UNA singola email di un piano editoriale già esistente. "
        "Mantieni la stessa data/posizione salvo indicazione contraria e resta coerente "
        "con brand, avatar e regola 80/20 del piano.\n\n"
        f"Email attuale da rigenerare:\n{json.dumps(current_email, ensure_ascii=False, indent=1)}\n\n"
        + (f"Istruzioni dell'utente: {instructions}\n\n" if instructions else "")
        + "Altre email del piano (NON rigenerarle, servono solo per coerenza):\n"
        + json.dumps(context.get("other_emails", []), ensure_ascii=False)
        + "\n\n"
        + _fmt_context(context)
    )
    return _call_claude(_SYSTEM, user, _EMAIL_SCHEMA, max_tokens=8000)
