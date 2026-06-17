"""ghl_sync.py — Sincronizza cartelle clienti Mailift con GoHighLevel.

Per ogni cartella in clients/ (escluse quelle interne):
  1. Legge README.md → estrae contatto, email, stato, MRR, prossimi step
  2. find_or_create_contact su GHL
  3. Aggiorna tag (mailift-retainer / mailift-prospect / mailift-one-shot / ecc.)
  4. Aggiunge/aggiorna nota con contesto completo

Usage:
    python tools/ghl_sync.py                    # sync tutti i clienti
    python tools/ghl_sync.py partylandia        # sync singolo cliente
    python tools/ghl_sync.py --dry-run          # mostra senza scrivere
    python tools/ghl_sync.py --pipelines        # mostra pipeline GHL disponibili
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl

# Cartelle da ignorare (interne, non clienti)
SKIP_FOLDERS = {"_mailift-team"}

# Mapping stato README → tag GHL
STATUS_TAG_MAP = [
    ("retainer attivo", "mailift-retainer"),
    ("retainer", "mailift-retainer"),
    ("setup", "mailift-setup"),
    ("one-shot", "mailift-one-shot"),
    ("ex cliente", "mailift-ex-cliente"),
    ("non attivo", "mailift-ex-cliente"),
    ("prospect", "mailift-prospect"),
    ("discovery", "mailift-prospect"),
    ("pending", "mailift-prospect"),
]

ALL_STATUS_TAGS = {v for _, v in STATUS_TAG_MAP}


def parse_readme(path: Path) -> dict:
    """Estrae dati strutturati da un README.md cliente."""
    text = path.read_text(encoding="utf-8")

    # Titolo H1 = nome azienda
    m = re.search(r"^#\s+(.+)$", text, re.M)
    azienda = m.group(1).strip() if m else path.parent.name

    def bold_field(name: str) -> str:
        # Formato: **Campo:** valore  oppure  **Campo**: valore
        # Il colon può essere dentro o fuori dai **
        n = re.escape(name)
        m = re.search(rf"\*\*{n}:?\*\*:?\s*(.+?)(?:\n|$)", text, re.I | re.M)
        return m.group(1).strip() if m else ""

    def table_field(name: str) -> str:
        m = re.search(
            rf"\|\s*\*\*{re.escape(name)}\*\*\s*\|\s*(.+?)\s*\|", text, re.I
        )
        return m.group(1).strip() if m else ""

    def field(name: str) -> str:
        v = bold_field(name) or table_field(name)
        v = v.strip("| ").strip()
        return "" if v in ("—", "-", "") else v

    contatto_raw = field("Contatto principale") or field("Owner")
    email_raw = field("Email") or field("email")
    stato = field("Stato") or table_field("Stato")
    mrr_raw = field("MRR attuale") or table_field("MRR")

    # Pulisci email (a volte contiene nomi, non email)
    email = ""
    if email_raw and "@" in email_raw:
        m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", email_raw)
        email = m.group(0) if m else ""

    # Estrai solo il nome dal "Nome (ruolo)" pattern
    contatto = re.sub(r"\s*\(.*?\)", "", contatto_raw).strip() if contatto_raw else ""
    parts = contatto.split() if contatto else []
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    # MRR numerico
    mrr = 0.0
    if mrr_raw:
        m = re.search(r"[\d.,]+", mrr_raw.replace(".", "").replace(",", "."))
        if m:
            try:
                mrr = float(m.group(0))
            except ValueError:
                pass

    # Ultima call
    m = re.search(r"_Ultima call:[^\n]+", text)
    ultima_call = m.group(0).replace("_", "").strip() if m else ""

    # Prossimi step Lorenzo
    m = re.search(r"### Lorenzo / Mailift\n(.*?)(?:###|\Z)", text, re.S)
    next_steps = m.group(1).strip() if m else ""

    # Ultime decisioni (bullets dopo l'intestazione)
    m = re.search(r"## Ultime decisioni\n.*?\n((?:- .+\n?)+)", text)
    ultime_decisioni = m.group(1).strip() if m else ""

    # Note operative
    m = re.search(r"## Note operative\n(.*?)(?:##|\Z)", text, re.S)
    note_op = m.group(1).strip() if m else ""

    return {
        "azienda": azienda,
        "folder": path.parent.name,
        "first_name": first_name,
        "last_name": last_name,
        "contatto_raw": contatto_raw,
        "email": email,
        "stato": stato,
        "mrr": mrr,
        "ultima_call": ultima_call,
        "next_steps": next_steps,
        "ultime_decisioni": ultime_decisioni,
        "note_op": note_op,
    }


def status_to_tags(stato: str) -> list[str]:
    stato_lower = stato.lower()
    tags = ["mailift-imported"]
    for keyword, tag in STATUS_TAG_MAP:
        if keyword in stato_lower:
            tags.append(tag)
            break
    return tags


def build_note(data: dict) -> str:
    lines = [
        f"📋 MAILIFT — {data['azienda']}",
        f"Stato: {data['stato'] or '—'}",
        f"MRR: {'€' + str(int(data['mrr'])) if data['mrr'] else '—'}",
        "",
    ]
    if data["ultima_call"]:
        lines += [f"🗓 {data['ultima_call']}", ""]
    if data["ultime_decisioni"]:
        lines += ["📌 Ultime decisioni:", data["ultime_decisioni"], ""]
    if data["next_steps"]:
        lines += ["✅ Prossimi step (Lorenzo):", data["next_steps"], ""]
    if data["note_op"]:
        lines += ["🔧 Note operative:", data["note_op"], ""]
    lines.append("— Sincronizzato da mailift-os/ghl_sync.py")
    return "\n".join(lines)


def sync_client(folder_path: Path, dry_run: bool = False) -> None:
    folder = folder_path.name
    readme = folder_path / "README.md"
    if not readme.exists():
        print(f"  ⚠️  {folder}: README.md non trovato, skip")
        return

    data = parse_readme(readme)
    tags = status_to_tags(data["stato"])
    note = build_note(data)

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}📁 {folder}")
    print(f"   Azienda:  {data['azienda']}")
    print(f"   Contatto: {data['contatto_raw'] or '—'}")
    print(f"   Email:    {data['email'] or '—'}")
    print(f"   Stato:    {data['stato'] or '—'}")
    print(f"   MRR:      {'€' + str(int(data['mrr'])) if data['mrr'] else '—'}")
    print(f"   Tags:     {', '.join(tags)}")

    if dry_run:
        return

    try:
        contact, created = ghl.find_or_create_contact(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            company_name=data["azienda"],
            source="mailift-os",
            tags=tags,
        )
        contact_id = contact.get("id", "")
        if not contact_id:
            print(f"  ❌ Impossibile ottenere ID contatto per {folder}")
            return

        action = "creato" if created else "trovato"
        print(f"   GHL: contatto {action} ({contact_id[:8]}...)")

        # Aggiorna tag (rimuovi vecchi tag mailift, aggiungi nuovi)
        current_tags = contact.get("tags", [])
        old_mailift_tags = [t for t in current_tags if t.startswith("mailift-")]
        for old_tag in old_mailift_tags:
            if old_tag not in tags:
                ghl.remove_tag(contact_id, old_tag)
        ghl.add_tags(contact_id, tags)

        # Aggiungi nota
        ghl.add_note(contact_id, note)
        print(f"   ✓ Nota aggiunta ({len(note)} chars)")

    except ghl.GHLError as exc:
        print(f"  ❌ GHL error: {exc}")


def show_pipelines() -> None:
    print("Pipeline GHL disponibili:\n")
    try:
        pipelines = ghl.list_pipelines()
        if not pipelines:
            print("  (nessuna pipeline trovata)")
            return
        for p in pipelines:
            print(f"  Pipeline: {p.get('name')} (id: {p.get('id')})")
            for stage in p.get("stages", []):
                print(f"    Stage: {stage.get('name')} (id: {stage.get('id')})")
    except ghl.GHLError as exc:
        print(f"❌ {exc}")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    show_pip = "--pipelines" in args
    targets = [a for a in args if not a.startswith("--")]

    if show_pip:
        show_pipelines()
        return

    clients_dir = PROJECT_ROOT / "clients"
    folders = (
        [clients_dir / t for t in targets]
        if targets
        else sorted(clients_dir.iterdir())
    )

    total = 0
    for folder in folders:
        if not folder.is_dir():
            print(f"⚠️  {folder.name}: cartella non trovata")
            continue
        if folder.name in SKIP_FOLDERS:
            continue
        sync_client(folder, dry_run=dry_run)
        total += 1

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}✅ Sync completato — {total} clienti processati")


if __name__ == "__main__":
    main()
