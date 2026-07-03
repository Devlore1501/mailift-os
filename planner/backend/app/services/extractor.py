"""Estrazione brand identity da documenti (PDF, testo).

Il cliente carica il brand book / questionario e Claude ne estrae profilo,
tono di voce, avatar e (se presenti) prodotti. In mock_mode si usa pypdf
per un'estrazione dimostrativa senza API.
"""

from __future__ import annotations

import base64
import io
import json
from typing import Any

from .. import settings as cfg

MAX_TOTAL_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "text",
    "text/markdown": "text",
}


class ExtractionError(Exception):
    pass


EXTRACT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "Cosa vende il brand, a chi, come. 2-4 frasi.",
        },
        "tone_of_voice": {"type": "string"},
        "mission": {"type": "string"},
        "positioning": {"type": "string"},
        "avatar": {
            "type": "object",
            "properties": {
                "who": {"type": "string"},
                "desires": {"type": "array", "items": {"type": "string"}},
                "objections": {"type": "array", "items": {"type": "string"}},
                "language": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["who", "desires", "objections", "language", "notes"],
            "additionalProperties": False,
        },
        "products": {
            "type": "array",
            "description": "Prodotti citati nei documenti, se presenti. Vuoto altrimenti.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "price": {"type": ["number", "null"]},
                    "is_best_seller": {"type": "boolean"},
                },
                "required": ["name", "category", "price", "is_best_seller"],
                "additionalProperties": False,
            },
        },
        "extraction_notes": {
            "type": "string",
            "description": "Cosa NON è stato trovato nei documenti e andrebbe completato a mano.",
        },
    },
    "required": [
        "description",
        "tone_of_voice",
        "mission",
        "positioning",
        "avatar",
        "products",
        "extraction_notes",
    ],
    "additionalProperties": False,
}

_SYSTEM = """Sei un brand strategist di un'agenzia di email marketing italiana.
Ricevi documenti di brand (brand book, questionari di onboarding, presentazioni,
pagine "chi siamo") e ne estrai il profilo per alimentare la generazione di email.

Regole:
- Scrivi in italiano, in modo concreto e utilizzabile (niente frasi vaghe da marketing).
- Estrai SOLO ciò che è supportato dai documenti; non inventare. Se un campo non è
  ricavabile, lascialo stringa vuota (o lista vuota) e segnalalo in extraction_notes.
- tone_of_voice: come scrive/parla il brand (registro, persona, stile), non i valori.
- avatar: il cliente tipo — chi è, cosa desidera, cosa lo frena, che linguaggio usa.
- products: solo prodotti/linee chiaramente identificabili, con prezzo solo se esplicito."""


def _mock_extract(files: list[tuple[str, bytes, str]]) -> dict:
    """Estrazione demo senza API: legge il testo del PDF e compila campi marcati."""
    text_parts: list[str] = []
    for filename, data, kind in files:
        if kind == "pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(data))
                for page in reader.pages[:10]:
                    text_parts.append(page.extract_text() or "")
            except Exception:
                text_parts.append(f"[testo non estraibile da {filename}]")
        else:
            text_parts.append(data.decode("utf-8", errors="replace"))
    text = " ".join(" ".join(text_parts).split())
    excerpt = text[:400] or "(documento vuoto)"
    return {
        "description": f"[DEMO — estratto senza API Claude] {excerpt}",
        "tone_of_voice": "[DEMO] Da definire: professionale ma caldo",
        "mission": "",
        "positioning": "",
        "avatar": {
            "who": "[DEMO] Cliente tipo da definire in base al documento",
            "desires": ["[DEMO] desiderio estratto"],
            "objections": ["[DEMO] obiezione estratta"],
            "language": "",
            "notes": "",
        },
        "products": [],
        "extraction_notes": (
            "Modalità demo: configurare ANTHROPIC_API_KEY per l'estrazione reale. "
            f"Letti {len(files)} file, {len(text)} caratteri di testo."
        ),
    }


def extract_profile(files: list[tuple[str, bytes, str]]) -> dict:
    """files: lista di (filename, bytes, kind) con kind 'pdf' | 'text'."""
    if cfg.mock_mode():
        return _mock_extract(files)

    import anthropic

    content: list[dict] = []
    for filename, data, kind in files:
        if kind == "pdf":
            content.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(data).decode("ascii"),
                    },
                    "title": filename,
                }
            )
        else:
            content.append(
                {
                    "type": "text",
                    "text": f"--- Documento: {filename} ---\n"
                    + data.decode("utf-8", errors="replace")[:100_000],
                }
            )
    content.append(
        {
            "type": "text",
            "text": "Estrai il profilo brand da questi documenti secondo lo schema richiesto.",
        }
    )

    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    try:
        with client.messages.stream(
            model=cfg.CLAUDE_MODEL,
            max_tokens=8000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_config={"format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
        ) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        raise ExtractionError(f"Errore API Claude: {e.message}") from e
    if message.stop_reason == "refusal":
        raise ExtractionError("L'analisi del documento è stata rifiutata dal modello.")
    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Risposta non valida dal modello: {e}") from e
