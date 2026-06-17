#!/usr/bin/env python3
"""Crea un file call.md dal summary Fathom (senza transcript completo).

Usage:
    python tools/create_call_from_summary.py <cliente> <data-YYYY-MM-DD> <titolo> <summary-text>

Oppure interattivo:
    python tools/create_call_from_summary.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date as Date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH     = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

CLIENTS_DIR   = PROJECT_ROOT / "clients"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

PROMPT_TMPL = """\
Sei la segretaria operativa di Lorenzo (Mailift). Hai il summary AI di una call Fathom con il cliente **{cliente}**.

Trasforma il summary in un report strutturato Mailift. Il summary è in formato "Sandler Selling System Notes" — devi estrarre le info utili e riformattarle.

Formato OUTPUT (markdown esatto):

---

# Call: [titolo breve]

**Data:** {data}
**Partecipanti:** [nomi/ruoli]
**Fonte:** Fathom AI Summary

## Riassunto esecutivo
[2-4 righe]

## Decisioni prese
- [decisioni concrete]

## Action items
### Lorenzo / Mailift
- [ ] [task]

### Cliente
- [ ] [task]

## Contesto aggiornato cliente
- [bullet point chiave sul cliente]

## Segnali importanti
[opportunità, rischi, flag strategici. Se nessuno: "Nessuno."]

## Note operative
[dettagli tecnici, vincoli, preferenze emerse]

---

Summary Fathom da trasformare:
{summary}
"""


def _extract_section(text: str, section: str) -> str:
    pattern = rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_title(text: str) -> str:
    m = re.search(r"^# Call: (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "call"


def _update_readme(cliente_dir: Path, call_file: Path, decisioni: str, action_items: str, data: str) -> None:
    readme = cliente_dir / "README.md"
    if not readme.exists():
        return
    content = readme.read_text()
    nuova_sezione = f"_Ultima call: [{data}](calls/{call_file.name})_\n\n{decisioni}"
    content = re.sub(
        r"## Ultime decisioni.*?(?=\n## |\Z)",
        f"## Ultime decisioni\n{nuova_sezione}\n\n",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"## Prossimi step.*?(?=\n## |\Z)",
        f"## Prossimi step\n{action_items}\n\n",
        content,
        flags=re.DOTALL,
    )
    readme.write_text(content)
    print(f"  ✓ README aggiornato")


def run(cliente: str, data: str, titolo: str, summary: str) -> Path:
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY non configurato")

    cliente_dir = CLIENTS_DIR / cliente
    calls_dir   = cliente_dir / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)

    prompt = PROMPT_TMPL.format(cliente=cliente, data=data, summary=summary)

    client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    report = message.content[0].text.strip()

    slug     = re.sub(r"[^\w\-]", "-", titolo.lower())[:50].strip("-")
    filename = f"{data}_{slug}.md"
    out_file = calls_dir / filename
    out_file.write_text(report)
    print(f"  ✓ {out_file.relative_to(PROJECT_ROOT)}")

    decisioni    = _extract_section(report, "Decisioni prese")
    action_items = _extract_section(report, "Action items")
    _update_readme(cliente_dir, out_file, decisioni, action_items, data)

    return out_file


if __name__ == "__main__":
    if len(sys.argv) == 5:
        run(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage: create_call_from_summary.py <cliente> <YYYY-MM-DD> <titolo> <summary>")
        sys.exit(1)
