"""
Daily Inbox Triage — orchestratore Layer 3 per workflows/daily_inbox_triage.md.

Per un account Gmail, nelle ultime N ore:
    1. Lista i messaggi in inbox
    2. Recupera headers + body
    3. Classifica via Anthropic in PROMO/INFO/ACTION/VIP
    4. Per ACTION/VIP crea task in Tasks_Mailift (Notion)
    5. Per PROMO archivia (rimuove label INBOX)
    6. Salva un report .tmp/inbox_triage_<account>_<date>.json

Usage:
    python tools/inbox_triage.py --account business --hours 24
    python tools/inbox_triage.py --account personal --hours 24 --dry-run
    python tools/inbox_triage.py --account business --hours 24 --send-report

`--send-report` invia il riepilogo a INBOX_TRIAGE_REPORT_TO. Senza il flag,
il report viene solo stampato e salvato in .tmp/.

Per coprire entrambi gli account, lancialo due volte con --account diversi.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "tools"))

from gmail_client import (  # noqa: E402
    archive_message,
    get_message,
    list_recent,
    load_service,
    send_email,
)
from classify_emails import classify_emails  # noqa: E402
from notion_tasks import (  # noqa: E402
    STATUS_DEFAULT,
    create_task,
    get_client as notion_client,
)


def _account_label(account: str) -> str:
    return "Personale" if account == "personal" else "Business"


def _account_address(account: str) -> str:
    key = "GMAIL_PERSONAL_ADDRESS" if account == "personal" else "GMAIL_BUSINESS_ADDRESS"
    return os.environ.get(key, "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily inbox triage per un account Gmail")
    ap.add_argument("--account", required=True, choices=["personal", "business"])
    ap.add_argument("--hours", type=int, default=24, help="Finestra temporale (default 24)")
    ap.add_argument("--max", type=int, default=200, help="Max messaggi da processare")
    ap.add_argument("--dry-run", action="store_true", help="Non archivia, non crea task, non invia report")
    ap.add_argument("--send-report", action="store_true", help="Invia il report via Gmail a INBOX_TRIAGE_REPORT_TO")
    args = ap.parse_args()

    account_label = _account_label(args.account)
    account_address = _account_address(args.account)
    today_iso = datetime.now().strftime("%Y-%m-%d")

    print(f"=== Inbox Triage — {account_label} ({account_address}) — ultime {args.hours}h ===")
    if args.dry_run:
        print("MODE: DRY-RUN (nessuna scrittura)")
    print()

    # 1. Gmail
    print("1) Carico Gmail service…")
    service = load_service(args.account)

    print(f"2) Lista messaggi in inbox (newer_than:{args.hours}h)…")
    listing = list_recent(service, hours=args.hours, max_results=args.max)
    print(f"   trovati {len(listing)} messaggi")

    if not listing:
        print("Nessun messaggio. Niente da fare.")
        return 0

    # 2. Fetch dettagli
    print("3) Recupero dettagli (headers + body)…")
    emails: list[dict] = []
    for i, m in enumerate(listing, 1):
        try:
            emails.append(get_message(service, m["id"]))
        except Exception as e:
            print(f"   WARN: get_message fallita per {m['id']}: {e}")
        if i % 10 == 0:
            print(f"   {i}/{len(listing)}")
    print(f"   {len(emails)} email pronte per la classificazione")

    # 3. Classifica
    print("4) Classifico via Anthropic…")
    results = classify_emails(emails, account_label=account_label, today_iso=today_iso)
    by_id = {r["id"]: r for r in results}

    counts = {"PROMO": 0, "INFO": 0, "ACTION": 0, "VIP": 0}
    for r in results:
        counts[r.get("category", "INFO")] = counts.get(r.get("category", "INFO"), 0) + 1
    print(f"   PROMO={counts['PROMO']}  INFO={counts['INFO']}  ACTION={counts['ACTION']}  VIP={counts['VIP']}")

    # 4. Notion + Archive
    notion = None
    notion_data_source = os.environ.get("NOTION_TASKS_DATA_SOURCE_ID", "")
    notion_user_id = os.environ.get("NOTION_USER_ID_LORENZO", "")
    if not args.dry_run and (counts["ACTION"] + counts["VIP"]) > 0:
        if not (notion_data_source and notion_user_id):
            print("ERRORE: NOTION_TASKS_DATA_SOURCE_ID o NOTION_USER_ID_LORENZO mancanti in .env")
            return 1
        notion = notion_client()

    created_tasks: list[dict] = []
    archived: list[dict] = []
    info_kept: list[dict] = []
    errors: list[dict] = []

    print("5) Eseguo azioni…")
    for email in emails:
        cls = by_id.get(email["id"])
        if not cls:
            print(f"   WARN: classificazione mancante per {email['id']}")
            continue
        cat = cls.get("category", "INFO")
        sender = email.get("from", "")
        subject = email.get("subject", "")

        if cat in ("ACTION", "VIP"):
            title_actionable = cls.get("actionable_title", "").strip() or subject
            confidence = cls.get("confidence", "high")
            prefix = f"[DA CONTROLLARE]" if confidence == "low" else f"[{account_label}]"
            full_title = f"{prefix} {title_actionable}".strip()


            received_at = email.get("date", "")
            context = cls.get("context_summary", "") or email.get("snippet", "")

            if args.dry_run:
                created_tasks.append({
                    "id": email["id"],
                    "title": full_title,
                    "from": sender,
                    "permalink": email["permalink"],
                    "category": cat,
                    "due_date": cls.get("due_date"),
                    "categoria": cls.get("categoria_notion", "Altro"),
                    "priorita": cls.get("priorita_notion", "Media"),
                    "dry_run": True,
                })
                print(f"   [DRY] TASK {full_title}")
            else:
                try:
                    page = create_task(
                        notion,
                        data_source_id=notion_data_source,
                        name=full_title,
                        assign_user_ids=[notion_user_id],
                        categoria=cls.get("categoria_notion", "Altro"),
                        priorita=cls.get("priorita_notion", "Media"),
                        due_date=cls.get("due_date"),
                        permalink=email["permalink"],
                        sender=sender,
                        account_label=account_label,
                        received_at=received_at,
                        context=context,
                        status=STATUS_DEFAULT,
                    )
                    created_tasks.append({
                        "id": email["id"],
                        "title": full_title,
                        "from": sender,
                        "permalink": email["permalink"],
                        "category": cat,
                        "notion_page_id": page.get("id"),
                        "notion_url": page.get("url"),
                        })
                    print(f"   TASK created: {full_title}")
                except Exception as e:
                    errors.append({"id": email["id"], "step": "create_task", "error": str(e), "title": full_title})
                    print(f"   ERROR create_task '{full_title}': {e}")

        elif cat == "PROMO":
            if args.dry_run:
                archived.append({
                    "id": email["id"], "from": sender, "subject": subject,
                    "permalink": email["permalink"], "dry_run": True,
                })
                print(f"   [DRY] ARCHIVE {sender[:50]} | {subject[:60]}")
            else:
                try:
                    archive_message(service, email["id"])
                    archived.append({
                        "id": email["id"], "from": sender, "subject": subject,
                        "permalink": email["permalink"],
                    })
                    print(f"   ARCHIVED: {sender[:50]} | {subject[:60]}")
                except Exception as e:
                    errors.append({"id": email["id"], "step": "archive", "error": str(e)})
                    print(f"   ERROR archive {email['id']}: {e}")

        else:  # INFO
            info_kept.append({
                "id": email["id"], "from": sender, "subject": subject,
                "permalink": email["permalink"],
            })

    # 5. Report
    report = {
        "account": args.account,
        "account_label": account_label,
        "account_address": account_address,
        "date": today_iso,
        "hours_window": args.hours,
        "dry_run": args.dry_run,
        "totals": {
            "received": len(emails),
            "promo_archived": len(archived),
            "info_kept": len(info_kept),
            "tasks_created": len(created_tasks),
            "errors": len(errors),
        },
        "tasks_created": created_tasks,
        "archived": archived,
        "info_kept": info_kept,
        "errors": errors,
    }

    out_dir = ROOT / ".tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"inbox_triage_{args.account}_{today_iso}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nReport JSON: {out_path}")

    # 6. Stampa riepilogo human-friendly
    print()
    print(_format_report_text(report))

    # 7. Invio report via email se richiesto
    if args.send_report and not args.dry_run:
        recipient = os.environ.get("INBOX_TRIAGE_REPORT_TO", "")
        if not recipient:
            print("WARN: INBOX_TRIAGE_REPORT_TO mancante, salto l'invio")
        else:
            subject = f"[Inbox Triage] {today_iso} {account_label} — {len(created_tasks)} task, {len(archived)} archiviate"
            body = _format_report_text(report)
            try:
                send_email(service, to=recipient, subject=subject, body=body)
                print(f"Report inviato a {recipient}")
            except Exception as e:
                print(f"ERRORE invio report: {e}")
                return 1

    return 0


def _format_report_text(report: dict) -> str:
    t = report["totals"]
    lines = [
        f"# Inbox Triage — {report['date']} — {report['account_label']} ({report['account_address']})",
        f"Finestra: ultime {report['hours_window']}h",
        "",
        f"- Ricevute:           {t['received']}",
        f"- Archiviate (PROMO): {t['promo_archived']}",
        f"- Info in inbox:      {t['info_kept']}",
        f"- Task creati:        {t['tasks_created']}",
    ]
    if t["errors"]:
        lines.append(f"- ERRORI:             {t['errors']}")
    if report["dry_run"]:
        lines.append("- [DRY-RUN: nessuna azione eseguita]")
    if report["tasks_created"]:
        lines.append("\n## Task creati")
        for tk in report["tasks_created"]:
            link = tk.get("notion_url") or "(dry-run)"
            lines.append(f"- {tk['title']}  →  {link}")
            lines.append(f"    da: {tk['from']}  |  thread: {tk['permalink']}")
    if report["info_kept"]:
        lines.append("\n## INFO lasciate in inbox")
        for it in report["info_kept"][:10]:
            lines.append(f"- {it['from']}: {it['subject']}")
        if len(report["info_kept"]) > 10:
            lines.append(f"  …e altre {len(report['info_kept']) - 10}")
    if report["archived"]:
        lines.append("\n## PROMO archiviate")
        for it in report["archived"][:15]:
            lines.append(f"- {it['from']}: {it['subject']}")
        if len(report["archived"]) > 15:
            lines.append(f"  …e altre {len(report['archived']) - 15}")
    if report["errors"]:
        lines.append("\n## Errori")
        for er in report["errors"]:
            lines.append(f"- [{er['step']}] {er.get('title', er['id'])}: {er['error']}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
