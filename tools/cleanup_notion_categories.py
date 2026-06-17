"""Cleanup one-shot per il database Tasks_Mailift di Notion.

Scansiona tutti i task aperti e propone Categoria + Priorita' inferite dal
titolo e dalla scadenza. Default: dry-run (mostra solo la proposta).
Per applicare: passare `--apply`.

Logica di inferenza
-------------------

**Categoria** dal titolo (case-insensitive, ordine = priorita' di match):
1. `[STRATEGIA]`, `[STRATEGY]`, "strategia", "segmentazione" → Strategia
2. `[COPY]`, "copy", "scrivi", "newsletter testi", "voice" → Copy
3. `[DESIGN]`, "design", "banner", "asset", "popup", "grafica" → Design
4. `[TECNICO]`, "setup", "integrazione", "API", "webhook", "make.com",
   "n8n", "klaviyo flow", "trigger" → Tecnico
5. `[REPORT]`, "report", "weekly", "metriche", "analisi" → Reportistica
6. `[Personale]`, "rinnovare", "polizza", "pagamento personale" → Altro
7. "fattura", "autofattura", "estratto conto", "Revolut" → Altro (admin)
8. "check", "verifica", "controllo" → Tecnico (di solito setup/QA)
9. fallback → Altro

**Priorita'** combinando scadenza + keyword:
- due_date overdue OR entro 3 giorni → Alta
- titolo contiene "URGENTE", "ASAP", "🔥", "critico" → Alta
- due_date entro 7 giorni → Media (se non gia' Alta)
- titolo contiene "importante", "rivedere", "decidere" → Media
- nessun match → Media (default conservativo)

L'inferenza e' deliberatamente conservativa: in dubbio si va su Media + Altro.

Usage:
    python tools/cleanup_notion_categories.py            # dry-run
    python tools/cleanup_notion_categories.py --apply    # applica davvero
    python tools/cleanup_notion_categories.py --apply --skip-categorized
        # applica solo a quelli senza categoria/priorita' (non sovrascrive)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.notion_tasks import (  # noqa: E402
    list_open_tasks,
    update_task_properties,
)


# ─── Regole di inferenza categoria ───────────────────────────────────────────

# Ogni regola: (lista_pattern_lowercase, categoria_target, descrizione_match)
CATEGORIA_RULES: list[tuple[list[str], str, str]] = [
    (
        [
            r"\[strateg",
            r"strategia",
            r"segmentazione",
            r"posizionamento",
            r"a/b test",
            r"ragionare",
            r"\bprospect\b",
            r"offerta",
            r"\boffer\b",
            r"hero product",
        ],
        "Strategia",
        "strategia/decisione",
    ),
    (
        [r"\[copy\]", r"copy ", r"newsletter testi", r"\bvoice\b"],
        "Copy",
        "copy/newsletter",
    ),
    (
        [r"\[design\]", r"\bdesign\b", r"banner", r"\bpopup\b", r"grafica", r"asset"],
        "Design",
        "design/asset",
    ),
    (
        [
            r"\[tecnico\]",
            r"setup",
            r"integrazione",
            r"\bapi\b",
            r"webhook",
            r"make\.com",
            r"\bn8n\b",
            r"klaviyo flow",
            r"\btrigger\b",
        ],
        "Tecnico",
        "setup/integrazione",
    ),
    (
        [
            r"\[report\]",
            r"report",
            r"weekly",
            r"metriche",
            r"analisi",
            r"questionario",
            r"\bbf\b",
            r"black friday",
            r"survey",
        ],
        "Reportistica",
        "report/analytics",
    ),
    (
        [
            r"check ",
            r"verifica",
            r"controllo",
            r"checkout flow",
        ],
        "Tecnico",
        "check/verifica (QA tecnico)",
    ),
    (
        [
            r"\[personale\]",
            r"rinnovare",
            r"polizza",
            r"pagamento personale",
        ],
        "Altro",
        "personale",
    ),
    (
        [
            r"fattura",
            r"autofattura",
            r"estratto conto",
            r"revolut",
            r"commercialista",
        ],
        "Altro",
        "amministrazione/fatture",
    ),
]


def infer_categoria(title: str) -> tuple[str, str]:
    """Ritorna (categoria, ragione_match). Default: ('Altro', 'fallback')."""
    t = title.lower()
    for patterns, cat, desc in CATEGORIA_RULES:
        for pat in patterns:
            if re.search(pat, t):
                return cat, desc
    return "Altro", "fallback (no pattern match)"


# ─── Regole di inferenza priorita ────────────────────────────────────────────

URGENT_KEYWORDS = (
    "urgente",
    "asap",
    "🔥",
    "critico",
    "subito",
    "emergenza",
)
IMPORTANT_KEYWORDS = (
    "importante",
    "rivedere",
    "decidere",
    "approva",
)


def infer_priorita(
    title: str, due_date: Optional[str], today_iso: str
) -> tuple[str, str]:
    """Ritorna (priorita, ragione)."""
    t = title.lower()

    # Calcolo distanza scadenza
    days_until: Optional[int] = None
    if due_date:
        try:
            due = date.fromisoformat(due_date)
            today = date.fromisoformat(today_iso)
            days_until = (due - today).days
        except ValueError:
            days_until = None

    # Alta: scaduto, entro 3 giorni, o keyword urgente
    if days_until is not None and days_until <= 3:
        if days_until < 0:
            return "Alta", f"overdue ({-days_until}gg)"
        return "Alta", f"scadenza imminente ({days_until}gg)"
    if any(kw in t for kw in URGENT_KEYWORDS):
        return "Alta", "keyword urgente"

    # Media: entro 7 giorni, o keyword importante
    if days_until is not None and days_until <= 7:
        return "Media", f"scadenza vicina ({days_until}gg)"
    if any(kw in t for kw in IMPORTANT_KEYWORDS):
        return "Media", "keyword importante"

    # Default
    return "Media", "default conservativo"


# ─── Main ────────────────────────────────────────────────────────────────────


def build_proposals(skip_categorized: bool) -> list[dict]:
    """Recupera i task aperti e costruisce le proposte di update."""
    tasks = list_open_tasks(only_lorenzo=True, include_unassigned=True)
    today_iso = date.today().isoformat()
    proposals: list[dict] = []

    for t in tasks:
        current_cat = t.get("categoria")
        current_pri = t.get("priorita")

        # Se entrambe gia' settate e flag --skip-categorized, salta
        if skip_categorized and current_cat and current_pri:
            continue

        new_cat, cat_reason = infer_categoria(t["name"])
        new_pri, pri_reason = infer_priorita(t["name"], t.get("due_date"), today_iso)

        # Cosa cambierebbe davvero?
        cat_changes = current_cat != new_cat
        pri_changes = current_pri != new_pri

        if not cat_changes and not pri_changes:
            continue

        proposals.append(
            {
                "id": t["id"],
                "name": t["name"],
                "current_categoria": current_cat,
                "new_categoria": new_cat if cat_changes else None,
                "categoria_reason": cat_reason if cat_changes else None,
                "current_priorita": current_pri,
                "new_priorita": new_pri if pri_changes else None,
                "priorita_reason": pri_reason if pri_changes else None,
                "due_date": t.get("due_date"),
                "status": t.get("status"),
            }
        )

    return proposals


def print_proposals(proposals: list[dict]) -> None:
    if not proposals:
        print("Nessuna proposta — tutti i task sono già categorizzati e prioritizzati.")
        return

    print(f"📋 Proposte di update: {len(proposals)} task da aggiornare\n")
    for i, p in enumerate(proposals, 1):
        print(f"{i:2}. {p['name']}")
        print(f"    id: {p['id']}")
        print(f"    status attuale: {p['status']}    due: {p['due_date'] or '—'}")

        if p["new_categoria"]:
            curr = p["current_categoria"] or "(vuoto)"
            print(
                f"    Categoria: {curr} → {p['new_categoria']}"
                f"   ← {p['categoria_reason']}"
            )
        if p["new_priorita"]:
            curr = p["current_priorita"] or "(vuoto)"
            print(
                f"    Priorita:  {curr} → {p['new_priorita']}"
                f"   ← {p['priorita_reason']}"
            )
        print()


def apply_proposals(proposals: list[dict]) -> dict:
    """Applica gli update a Notion. Ritorna report success/fail."""
    report = {"total": len(proposals), "succeeded": [], "failed": []}
    for p in proposals:
        try:
            kwargs: dict = {}
            if p["new_categoria"]:
                kwargs["categoria"] = p["new_categoria"]
            if p["new_priorita"]:
                kwargs["priorita"] = p["new_priorita"]
            update_task_properties(page_id=p["id"], **kwargs)
            report["succeeded"].append({"id": p["id"], "name": p["name"]})
            print(f"  ✅ {p['name']}")
        except Exception as exc:  # noqa: BLE001
            report["failed"].append(
                {"id": p["id"], "name": p["name"], "error": f"{type(exc).__name__}: {exc}"}
            )
            print(f"  ❌ {p['name']}: {exc}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica davvero gli update (default: dry-run)",
    )
    parser.add_argument(
        "--skip-categorized",
        action="store_true",
        help="Non sovrascrivere task gia' categorizzati e prioritizzati",
    )
    args = parser.parse_args()

    print("[cleanup_notion] pull task aperti...")
    proposals = build_proposals(skip_categorized=args.skip_categorized)

    print_proposals(proposals)

    if not args.apply:
        print("\n💡 Dry-run completato. Per applicare:")
        print("    python tools/cleanup_notion_categories.py --apply")
        return

    if not proposals:
        return

    print(f"\n🚀 Applicando {len(proposals)} update a Notion...")
    report = apply_proposals(proposals)
    print(
        f"\nRiepilogo: {len(report['succeeded'])}/{report['total']} ok, "
        f"{len(report['failed'])} errori"
    )


if __name__ == "__main__":
    main()
