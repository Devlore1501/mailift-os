"""Raccoglie il contesto completo di un contatto GHL per la scrittura degli
'spunti per riattivazione' (workflow Recupero Lead Ads).

Per ogni contatto: note, custom field valorizzati (nome risolto), stage
opportunità (nome risolto), e gli ultimi messaggi (email/SMS/WhatsApp) di
ogni conversazione.

Uso:
    python tools/gather_reactivation_context.py <contact_id> [<contact_id> ...]
    python tools/gather_reactivation_context.py --tag lead-freddo-30gg --exclude-tag "non qualificato" [--limit N]

Output: JSON su stdout (list di dict), oppure --out file.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import ghl_client as g

STAGE_NAMES = {
    "d8e48c05-3a13-470c-b305-0a30221954fa": "Lead",
    "8020aaa0-8189-4cb5-a0af-56dfcbfdf674": "Scarica calcolatore",
    "0e431d6e-ee87-4ace-bb3e-15c08585a90c": "Non risponde 1/5",
    "70eaceb3-f452-43b3-90db-ea3a212393cd": "Cooldown",
    "34e239b6-2650-4508-b040-37ba81a8cbf3": "Da contattare in futuro",
    "55478c71-985a-434c-b103-5342d754685a": "Fissata call analisi",
    "1a022cc5-179f-49cf-bfc2-4a26e9465ab6": "No show",
    "fdb682f9-3c51-4335-bb95-a0055d277419": "Report",
    "2789e1e1-509b-4fa7-84af-3664dafed78f": "Show up",
    "2a8a160f-f748-4f14-bb25-a95a491c36aa": "Presentazione offerta",
    "d12c869b-ba6c-4da4-be1f-363424751291": "Follow-up manuale",
    "bd71ed3d-b190-46cb-8509-6d555c9ad3fc": "Non chiuso",
    "e8fd6775-b433-4c3a-a741-5e66a1173b4e": "Non qualificati",
    "4ad45936-435c-4f0f-810d-ee01e0e16318": "Chiuso",
    "4b069054-c3b9-499d-b4fd-2698443553a4": "Contratto",
    "a557ab83-6fe2-487a-aa87-e66ee02be3a1": "Onboarding",
}

# Stage che implicano quasi certamente che una discovery call si sia svolta.
DISCOVERY_CALL_HAPPENED_STAGES = {
    "Show up",
    "Report",
    "Presentazione offerta",
    "Follow-up manuale",
    "Non chiuso",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


def _custom_fields_by_id() -> dict[str, dict]:
    return {f["id"]: f for f in g.list_custom_fields()}


def gather_contact_context(contact_id: str, field_map: dict[str, dict]) -> dict:
    contact = g.get_contact(contact_id)

    custom_fields = []
    for cf in contact.get("customFields", []):
        meta = field_map.get(cf.get("id"), {})
        value = cf.get("value")
        if value in (None, "", []):
            continue
        custom_fields.append({"name": meta.get("name", cf.get("id")), "value": value})

    notes = [n.get("body", "") for n in g.list_notes(contact_id) if n.get("body")]

    opportunities = g.get_opportunities_for_contact(contact_id)
    stages = [
        STAGE_NAMES.get(o.get("pipelineStageId"), o.get("pipelineStageId"))
        for o in opportunities
        if o.get("pipelineStageId")
    ]
    discovery_call_likely = any(s in DISCOVERY_CALL_HAPPENED_STAGES for s in stages)

    activity = [
        {
            "stage": STAGE_NAMES.get(o.get("pipelineStageId"), o.get("pipelineStageId")),
            "created_at": o.get("createdAt"),
            "last_stage_change_at": o.get("lastStageChangeAt"),
            "source": o.get("source"),
        }
        for o in opportunities
    ]

    conversations = g.get_conversations_for_contact(contact_id)
    messages = []
    for convo in conversations:
        for m in g.get_messages_for_conversation(convo["id"])[:20]:
            body = _strip_html(m.get("body", ""))
            if not body:
                continue
            messages.append(
                {
                    "date": m.get("dateAdded"),
                    "direction": m.get("direction"),
                    "type": m.get("messageType"),
                    "body": body[:2000],
                }
            )
    messages.sort(key=lambda m: m.get("date") or "")

    return {
        "contact_id": contact_id,
        "first_name": contact.get("firstName"),
        "last_name": contact.get("lastName"),
        "company_name": contact.get("companyName"),
        "tags": contact.get("tags", []),
        "stages": stages,
        "activity": activity,
        "discovery_call_likely": discovery_call_likely,
        "custom_fields": custom_fields,
        "notes": notes,
        "messages": messages,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("contact_ids", nargs="*")
    parser.add_argument("--tag", help="Tag da includere nella ricerca")
    parser.add_argument("--exclude-tag", action="append", default=[], help="Tag da escludere (ripetibile)")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", help="File di output JSON (default: stdout)")
    args = parser.parse_args()

    if args.tag:
        contacts = g.search_contacts_by_tags([args.tag], exclude_tags=args.exclude_tag, limit=args.limit)
        contact_ids = [c["id"] for c in contacts]
    else:
        contact_ids = args.contact_ids

    if not contact_ids:
        print("Nessun contact_id fornito (usa argomenti posizionali o --tag).", file=sys.stderr)
        sys.exit(2)

    field_map = _custom_fields_by_id()
    results = []
    for i, cid in enumerate(contact_ids, 1):
        print(f"[{i}/{len(contact_ids)}] {cid}", file=sys.stderr)
        try:
            results.append(gather_contact_context(cid, field_map))
        except g.GHLError as exc:
            print(f"  errore su {cid}: {exc}", file=sys.stderr)

    out = json.dumps(results, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out)
        print(f"Scritto {len(results)} contatti su {args.out}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
