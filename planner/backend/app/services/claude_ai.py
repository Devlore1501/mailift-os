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
        "format": {
            "type": "string",
            "enum": ["grafica", "testuale"],
            "description": "grafica = email visuale montata in Canva; testuale = email in prosa stile 1:1",
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
            "description": "Solo per format=testuale: email completa in prosa (hook, corpo, CTA). "
            "Stringa vuota per le email grafiche.",
        },
        "blocks": {
            "type": "array",
            "description": "Solo per format=grafica: scaletta copy per il designer, un blocco "
            "per sezione della grafica. Lista vuota per le email testuali.",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["banner", "sezione", "info", "cta_finale"],
                    },
                    "headline": {"type": "string", "description": "Max 7 parole. Vuota se non serve."},
                    "subheadline": {"type": "string", "description": "Max 14 parole. Vuota se non serve."},
                    "text": {"type": "string", "description": "Micro-copy, max 25 parole. Vuota se non serve."},
                    "cta": {"type": "string", "description": "Testo bottone, max 4 parole. Vuota se non serve."},
                    "visual": {
                        "type": "string",
                        "description": "Indicazione visiva per il designer: cosa mostrare e come "
                        "(es. 'infografica 3 step numerati con icone', 'griglia 2x2 prodotti', "
                        "'confronto prima/dopo', 'badge sconto grande'). Vuota se non serve.",
                    },
                },
                "required": ["type", "headline", "subheadline", "text", "cta", "visual"],
                "additionalProperties": False,
            },
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
        "campaign": {
            "type": ["object", "null"],
            "description": "Solo se l'email fa parte di una sequenza lancio/promo: nome della "
            "sequenza e ruolo dell'email nella sequenza. null per le email normali.",
            "properties": {
                "name": {"type": "string"},
                "role": {
                    "type": "string",
                    "enum": [
                        "teaser",
                        "annuncio",
                        "follow_up",
                        "last_call",
                        "final_reminder",
                        "altro",
                    ],
                },
            },
            "required": ["name", "role"],
            "additionalProperties": False,
        },
    },
    "required": [
        "position",
        "send_date",
        "send_day",
        "send_time",
        "objective",
        "format",
        "theme",
        "angle",
        "segment",
        "subject_variants",
        "preview_text",
        "body",
        "blocks",
        "products",
        "offer",
        "template_notion_page_id",
        "campaign",
    ],
    "additionalProperties": False,
}

_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "emails": {"type": "array", "items": _EMAIL_SCHEMA},
        "campaigns": {
            "type": "array",
            "description": "Una voce per OGNI lancio/promo pianificato nel mese: spiegazione "
            "della strategia della sequenza e proposte extra. Vuoto se non ci sono lanci/promo.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "kind": {"type": "string", "enum": ["lancio", "promo"]},
                    "strategy": {
                        "type": "string",
                        "description": "Spiegazione della strategia scelta per la sequenza: "
                        "quante email, quando, con quali leve e segmenti, e perché.",
                    },
                    "proposals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-4 proposte extra concrete per potenziare la sequenza",
                    },
                },
                "required": ["name", "kind", "strategy", "proposals"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["emails", "campaigns"],
    "additionalProperties": False,
}

_SYSTEM = """Sei un email marketing strategist senior specializzato in eCommerce DTC su Klaviyo.
Lavori per un'agenzia italiana e produci calendari editoriali email MENSILI pronti da eseguire.

Regole non negoziabili:
- Scrivi SEMPRE in italiano, nel tono di voce del brand e nel linguaggio del suo avatar.
- Regola 70/20/10 sul mese: ~70% email EDUCATIVE (objective "nurturing" o "storytelling": \
consigli, guide, dietro le quinte, storie), ~20% email PRODOTTO (objective "vendita": focus \
su un prodotto, benefici e casi d'uso, senza sconti aggressivi), ~10% email PROMOZIONALI \
(objective "promo": sconti e offerte). Esempio con 12 email: 8-9 educative, 2-3 prodotto, \
1 promo. Le promo vanno collocate nei momenti a maggiore intento d'acquisto del mese.
- Calendario per paese: considera festività nazionali, ponti, ricorrenze e momenti \
commerciali del paese di destinazione indicato nel contesto, nel mese pianificato. Usa le \
occasioni fornite dall'utente e integra quelle rilevanti che conosci (es. festività \
nazionali, giornate a tema pertinenti al brand). Collega le email a queste date quando ha \
senso, senza forzature.
- Scegli i segmenti in base ai DATI Klaviyo forniti: se l'engagement è basso ("poor"), \
restringi gli invii ai segmenti engaged e includi una email di re-engagement verso gli inattivi. \
Se non ci sono dati, proponi segmenti standard e spiegalo nel rationale.
- Due FORMATI di email, da bilanciare sul mese: ~60% "grafica" e ~40% "testuale", mai più di \
due email dello stesso formato consecutive quando possibile. Promo e prodotto tendenzialmente \
grafiche; storytelling/nurturing in prima persona funzionano meglio testuali. Alternare i \
formati evita di mandare solo immagini (engagement e deliverability).
- Email TESTUALI: body in prosa completa e pronta all'uso, come una mail personale 1:1 \
(hook forte nelle prime 2 righe, UN solo angolo, una CTA chiara, 120-250 parole, niente \
riferimenti a elementi grafici). blocks = [] e template_notion_page_id = null.
- Email GRAFICHE: body = "" e compila blocks, la SCALETTA PER IL DESIGNER che semplifica la \
creazione in Canva. Struttura: primo blocco "banner" (headline ≤ 7 parole, subheadline ≤ 14, \
CTA breve, visual d'impatto); poi 2-4 blocchi "sezione" con micro-copy (≤ 25 parole l'uno) e \
campo visual che dice COSA mostrare; eventuale blocco "info" (spedizione, garanzia, codice \
sconto); chiudi con "cta_finale". EVITA MURI DI TESTO: quando il contenuto lo permette, \
trasforma il testo in infografica (step numerati, icone + micro-copy, griglie prodotto, \
confronti prima/dopo, percentuali grandi, badge) e descrivilo nel campo visual.
- Usa {{ first_name|default:'' }} come merge tag Klaviyo se serve personalizzazione.
- Oggetti: 2-3 varianti brevi (max ~45 caratteri), curiosità o beneficio, mai clickbait vuoto.
- Per ogni email GRAFICA scegli dal catalogo template fornito il template Canva più adatto al \
tipo di email e ritorna il suo notion_page_id (null solo se il catalogo è vuoto). Per le \
email testuali template_notion_page_id = null.
- Distribuisci gli invii lungo TUTTO il mese in modo regolare (mai due email nello stesso \
giorno, evita buchi di oltre una settimana), orari mattina 8:30-10:00 nei feriali; il weekend \
va bene 9:30-11:00. Se le performance passate suggeriscono altro, adeguati.
- Usa solo prodotti e offerte realmente forniti; non inventare sconti o codici.

LANCI E PROMO (sezione "Lanci e promo del mese" nel contesto):
- Un lancio o una promo NON è mai una singola email: è una SEQUENZA COORDINATA integrata nel \
calendario del mese. Etichetta OGNI email della sequenza col campo campaign {name, role} \
(name = nome del lancio/promo); tutte le altre email hanno campaign = null. Le email della \
sequenza contano nella quota 10% promo (per le promo) e 20% prodotto (per i lanci): riduci le \
altre promo/vendita del mese di conseguenza — la parte educativa resta ~70%.
- SEQUENZA PROMO — procedura dell'agenzia, testata su 30+ brand (per sale di 5-7 giorni):
  1. "teaser" 1-3 giorni prima dell'inizio: email hype "non comprare oggi" — consiglia di \
NON acquistare ora perché sta arrivando una sale (costruisce fiducia), invita a RISPONDERE \
alla mail per saperlo in anteprima (le risposte migliorano la deliverability), countdown \
all'inizio. NON rivelare lo sconto.
  2. "annuncio" il giorno di inizio: email grafica semplicissima leggibile a colpo d'occhio \
— header sale, sconto in grande, CTA, una riga di info. Verifica link e codice.
  3. "follow_up" a giorni alterni se la sale dura più di 3 giorni (sale di 5 giorni: giorno \
3; sale di 7: giorni 3 e 5): non limitarti a ripetere la promo, aggiungi contenuto — best \
seller, recensioni/social proof. Il formato TESTUALE 1:1 stile "customer support" è quello \
che converte meglio come follow-up.
  4. "last_call" la MATTINA dell'ultimo giorno: urgenza e scarsità, countdown alla fine, \
best seller, risparmio evidenziato.
  5. "final_reminder" la SERA dell'ultimo giorno (<5 ore alla fine), sempre TESTUALE: \
target = chi ha cliccato le email della sequenza SENZA acquistare (escludi acquirenti degli \
ultimi 20 giorni) — descrivi questo segmento e la sua logica nel rationale.
  Durate brevi: 3 giorni = annuncio + last_call + final_reminder (niente follow_up); \
flash 48h = annuncio, last_call, final_reminder; flash 24h = solo annuncio + last_call.
- SEQUENZA LANCIO prodotto: "teaser" di anticipazione ~5-7 giorni prima (mistero, dietro le \
quinte, waitlist), eventuale secondo teaser più vicino, "annuncio" il giorno del lancio \
(hero del prodotto, perché esiste, per chi è), "follow_up" con social proof/casi d'uso, \
"last_call" solo se c'è un'offerta lancio a scadenza.
- Nel campo "campaigns" del piano compila una voce per OGNI lancio/promo: in "strategy" \
spiega la logica della sequenza scelta (quante email, in quali date e perché, formati, \
segmenti e leve psicologiche), in "proposals" 2-4 proposte extra concrete e attuabili (es. \
countdown timer nelle grafiche, estensione riservata ai VIP, segmento winback dedicato, SMS \
di supporto). Se non ci sono lanci/promo nel mese: campaigns = [] e campaign = null ovunque."""

_OCCASIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "date": {"type": "string", "description": "ISO YYYY-MM-DD"},
                    "kind": {
                        "type": "string",
                        "enum": ["festività", "ponte", "ricorrenza"],
                    },
                    "idea": {
                        "type": "string",
                        "description": "Idea concreta di email/contenuto per il brand su questa data",
                    },
                },
                "required": ["name", "date", "kind", "idea"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}

_OCCASIONS_SYSTEM = """Sei un calendar strategist di un'agenzia di email marketing italiana.
Dato un paese, un mese e il contesto di un brand eCommerce, elenchi le date utili del mese:
- festività nazionali e ricorrenze religiose/civili del paese
- ponti e long weekend (indica il ponte, non solo la festività)
- ricorrenze commerciali e giornate a tema RILEVANTI per il brand (es. giornata mondiale
  del vino per una cantina); ometti quelle irrilevanti.
Per ogni data proponi UN'idea concreta di email coerente con brand e avatar (in italiano).
Includi solo date che cadono nel mese richiesto. 4-10 suggerimenti, i più rilevanti."""


def _fmt_context(context: dict) -> str:
    """Serializza il contesto brand in un blocco leggibile per il prompt."""
    brand = context["brand"]
    parts = [
        "## Brand",
        f"Nome: {brand['name']}",
        f"Paese di destinazione: {context.get('country') or brand.get('country') or 'IT'}",
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
        "## Lanci e promo del mese (ognuno = una sequenza email dedicata)",
        json.dumps(context.get("launches", []), ensure_ascii=False, indent=1) or "[]",
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
        f"Genera il calendario editoriale email per il mese che inizia il "
        f"{context['month_start']}. Numero email richieste: {context['num_emails']} "
        f"(rispetta la regola 70/20/10).\n"
        + (f"Indicazioni extra dell'utente: {context['notes']}\n" if context.get("notes") else "")
        + "\n"
        + _fmt_context(context)
    )
    plan = _call_claude(_SYSTEM, user, _PLAN_SCHEMA)
    emails = plan.get("emails", [])
    # normalizza le position
    for i, e in enumerate(emails, start=1):
        e["position"] = i
    return {"emails": emails, "campaigns": plan.get("campaigns") or []}


def regenerate_email(context: dict, current_email: dict, instructions: str) -> dict:
    """Rigenera una singola email del piano mantenendo coerenza col resto."""
    if cfg.mock_mode():
        return mockdata.mock_regenerated_email(current_email, instructions)

    user = (
        "Rigenera UNA singola email di un calendario editoriale mensile già esistente. "
        "Mantieni la stessa data/posizione salvo indicazione contraria e resta coerente "
        "con brand, avatar e regola 70/20/10 del piano.\n\n"
        f"Email attuale da rigenerare:\n{json.dumps(current_email, ensure_ascii=False, indent=1)}\n\n"
        + (f"Istruzioni dell'utente: {instructions}\n\n" if instructions else "")
        + "Altre email del piano (NON rigenerarle, servono solo per coerenza):\n"
        + json.dumps(context.get("other_emails", []), ensure_ascii=False)
        + "\n\n"
        + _fmt_context(context)
    )
    return _call_claude(_SYSTEM, user, _EMAIL_SCHEMA, max_tokens=8000)


def suggest_occasions(brand: dict, country: str, month: str) -> list[dict]:
    """Analizza festività/ponti/ricorrenze del paese nel mese e propone idee email."""
    if cfg.mock_mode():
        return mockdata.mock_occasion_suggestions(country, month)

    user = (
        f"Paese: {country}\nMese: {month}\n\n"
        "## Brand\n"
        + json.dumps(brand, ensure_ascii=False, indent=1)
        + "\n\nElenca le date utili del mese con un'idea email per ciascuna."
    )
    result = _call_claude(_OCCASIONS_SYSTEM, user, _OCCASIONS_SCHEMA, max_tokens=4000)
    # tieni solo le date effettivamente nel mese richiesto
    return [s for s in result.get("suggestions", []) if s.get("date", "").startswith(month)]
