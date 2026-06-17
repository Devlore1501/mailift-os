#!/usr/bin/env python3
"""Process Call — processa la trascrizione di una call e aggiorna il repo clienti.

Legge una trascrizione (file o stdin), la manda a Claude, e produce:
  - Un file markdown strutturato in clients/<cliente>/calls/YYYY-MM-DD_<titolo>.md
  - Aggiorna clients/<cliente>/README.md con ultime decisioni e prossimi step

Usage:
    python tools/process_call.py                          # wizard interattivo
    python tools/process_call.py <cliente> <file.txt>    # da file
    python tools/process_call.py <cliente> -              # da stdin (pipe)

Esempi:
    python tools/process_call.py bergamo-vini call.txt
    pbpaste | python tools/process_call.py le-rive -
    python tools/process_call.py riccardo-coach trascrizione.txt
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH     = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else PROJECT_ROOT / ".env")

CLIENTS_DIR   = PROJECT_ROOT / "clients"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

VALID_CLIENTS = [d.name for d in CLIENTS_DIR.iterdir() if d.is_dir()] if CLIENTS_DIR.exists() else []


# ── Prompt ────────────────────────────────────────────────────────────────────

def _build_prompt(cliente: str, trascrizione: str) -> str:
    return f"""Sei la segretaria operativa di Lorenzo, founder di Mailift Srl (agenzia email marketing per eCommerce DTC italiano).

Hai ricevuto la trascrizione di una call con il cliente **{cliente}**.

Analizza la trascrizione e produci un report strutturato in markdown con questo formato ESATTO:

---

# Call: [titolo breve che descrive l'argomento principale]

**Data:** [data della call se menzionata, altrimenti "da confermare"]
**Partecipanti:** [nomi/ruoli menzionati]
**Durata:** [se menzionata]

## Riassunto esecutivo
[2-4 righe che catturano l'essenza della call — cosa si è deciso, qual era il tema]

## Decisioni prese
- [ogni decisione concreta presa durante la call]
- [...]

## Action items
### Lorenzo / Mailift
- [ ] [cosa deve fare Lorenzo, con deadline se menzionata]
- [ ] [...]

### Cliente
- [ ] [cosa deve fare il cliente]
- [ ] [...]

## Contesto aggiornato cliente
[3-6 bullet point che aggiornano il profilo del cliente: nuove info su business, obiettivi, problemi, opportunità, preferenze emerse]

## Segnali importanti
[Eventuali segnali di rischio (insoddisfazione, budget in discussione), opportunità di upsell, o info strategiche che Lorenzo deve tenere a mente. Se nessuno, scrivi "Nessuno."]

## Note operative
[Qualsiasi dettaglio tecnico, preferenza su tono/frequenza email, vincoli specifici emersi]

---

Trascrizione:
{trascrizione}"""


# ── Aggiornamento README cliente ──────────────────────────────────────────────

def _update_readme(cliente_dir: Path, call_file: Path, decisioni: str, action_items: str, data: str) -> None:
    readme = cliente_dir / "README.md"
    if not readme.exists():
        return

    content = readme.read_text()

    # Aggiorna sezione "Ultime decisioni"
    nuova_sezione = f"_Ultima call: [{data}](calls/{call_file.name})_\n\n{decisioni}"
    content = re.sub(
        r"## Ultime decisioni.*?(?=\n## |\Z)",
        f"## Ultime decisioni\n{nuova_sezione}\n\n",
        content,
        flags=re.DOTALL,
    )

    # Aggiorna sezione "Prossimi step"
    content = re.sub(
        r"## Prossimi step.*?(?=\n## |\Z)",
        f"## Prossimi step\n{action_items}\n\n",
        content,
        flags=re.DOTALL,
    )

    readme.write_text(content)
    print(f"  ✓ README aggiornato: {readme}")


def _extract_section(text: str, section: str) -> str:
    """Estrae il contenuto di una sezione dal markdown."""
    pattern = rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_title(text: str) -> str:
    m = re.search(r"^# Call: (.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else "call"


# ── Wizard interattivo ────────────────────────────────────────────────────────

def _wizard() -> tuple[str, str]:
    print("\n=== Process Call ===\n")
    print("Clienti disponibili:")
    for i, c in enumerate(VALID_CLIENTS, 1):
        print(f"  {i}. {c}")
    print()

    scelta = input("Scegli cliente (numero o nome): ").strip()
    if scelta.isdigit():
        idx = int(scelta) - 1
        cliente = VALID_CLIENTS[idx] if 0 <= idx < len(VALID_CLIENTS) else scelta
    else:
        cliente = scelta

    print(f"\nIncolla la trascrizione della call con {cliente}.")
    print("Quando hai finito, premi INVIO due volte + digita 'END' + INVIO:\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    trascrizione = "\n".join(lines).strip()
    return cliente, trascrizione


# ── Main ──────────────────────────────────────────────────────────────────────

def run(cliente: str, trascrizione: str) -> None:
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY non configurato nel .env")
    if not trascrizione.strip():
        raise RuntimeError("Trascrizione vuota.")

    cliente_dir = CLIENTS_DIR / cliente
    if not cliente_dir.exists():
        # Crea il cliente al volo
        (cliente_dir / "calls").mkdir(parents=True)
        print(f"  → Nuovo cliente creato: {cliente}")
    calls_dir = cliente_dir / "calls"
    calls_dir.mkdir(exist_ok=True)

    print(f"\n[process-call] Cliente: {cliente} | {len(trascrizione)} caratteri trascrizione")
    print("  → Analisi AI in corso...")

    client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        messages=[{"role": "user", "content": _build_prompt(cliente, trascrizione)}],
    )
    report = message.content[0].text.strip()

    # Nome file
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    titolo   = _extract_title(report)
    slug     = re.sub(r"[^\w\-]", "-", titolo.lower())[:50].strip("-")
    filename = f"{today}_{slug}.md"
    out_file = calls_dir / filename

    # Scrivi il file call
    out_file.write_text(report)
    print(f"  ✓ File salvato: clients/{cliente}/calls/{filename}")

    # Aggiorna README
    decisioni    = _extract_section(report, "Decisioni prese")
    action_items = _extract_section(report, "Action items")
    _update_readme(cliente_dir, out_file, decisioni, action_items, today)

    print(f"\n✅ Call processata!")
    print(f"   File: clients/{cliente}/calls/{filename}")
    print(f"\n--- ANTEPRIMA ---")
    # Mostra le prime righe del report
    preview = "\n".join(report.split("\n")[:20])
    print(preview)
    print("---")
    print(f"\nPer committare: git add clients/ && git commit -m 'Call {cliente} {today}'")


if __name__ == "__main__":
    if not VALID_CLIENTS:
        print("❌ Cartella clients/ non trovata. Esegui dalla root del progetto.")
        sys.exit(1)

    try:
        if len(sys.argv) == 1:
            # Wizard interattivo
            cliente, trascrizione = _wizard()
        elif len(sys.argv) == 2:
            # Solo cliente → wizard per la trascrizione
            cliente = sys.argv[1]
            print(f"Incolla la trascrizione per {cliente}. Finisci con 'END' su una riga:")
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                except EOFError:
                    break
            trascrizione = "\n".join(lines)
        elif len(sys.argv) == 3:
            cliente = sys.argv[1]
            src     = sys.argv[2]
            if src == "-":
                trascrizione = sys.stdin.read()
            else:
                trascrizione = Path(src).read_text()
        else:
            print(__doc__)
            sys.exit(1)

        run(cliente, trascrizione)

    except (KeyboardInterrupt, EOFError):
        print("\nAnnullato.")
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
