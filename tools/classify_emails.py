"""
Classifica un batch di email per il workflow Daily Inbox Triage.

Per ciascuna email il modello produce:
    {
        "id": "<gmail message id>",
        "category": "PROMO" | "INFO" | "ACTION" | "VIP",
        "confidence": "high" | "medium" | "low",
        "reason": "spiegazione breve",
        "actionable_title": "verbo + oggetto, in italiano",  # solo se ACTION/VIP
        "due_date": "YYYY-MM-DD" | null,                      # se estraibile
        "categoria_notion": "Strategia"|"Copy"|"Design"|"Tecnico"|"Reportistica"|"Altro",
        "priorita_notion": "Alta"|"Media"|"Bassa",
        "context_summary": "2-3 righe di contesto",
        "suggested_cliente_query": "stringa breve" | ""       # per lookup nel DB Clienti
    }

Il batch e' una sola chiamata Anthropic con tool_use per output strutturato.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path.home() / ".secrets" / "mailift" / ".env"
load_dotenv(ENV_PATH if ENV_PATH.exists() else ROOT / ".env")

SYSTEM_PROMPT = """Sei un assistente personale per il triage giornaliero della casella email di Lorenzo Baretta, founder di Mailift Srl (agenzia di email marketing).

Per ogni email ricevuta devi assegnare UNA categoria fra:
- PROMO  = newsletter, marketing, promozioni, notifiche social, transazionali impersonali. Va archiviata.
- INFO   = comunicazione passiva, riepiloghi, comunicazioni di servizio, niente azione richiesta. Resta in inbox ma non genera task.
- ACTION = richiede risposta, decisione, conferma, firma, approvazione, scadenza. Genera task in Notion.
- VIP    = email da mittente in whitelist VIP. Si comporta come ACTION (per ora la whitelist e' vuota, quindi questa categoria sara' rara).

REGOLE DI CLASSIFICAZIONE (in ordine, prima che fa match vince):
1. Se header List-Unsubscribe presente E mittente non e' un cliente Mailift conosciuto -> probabile PROMO.
2. Mittenti tipici PROMO: newsletter, mailchimp, sendgrid, hubspot, klaviyo, mailerlite, instagram, facebook, linkedin updates, tiktok, learnn, learnn team, plaud, mailsuite daily report, infobusiness/marketing newsletter italiani.
3. Subject con pattern marketing ("offerta", "% sconto", "ultimo giorno", "black friday", "saldi", emoji marketing) -> PROMO se non c'e' richiesta esplicita.
4. ACTION se: domanda diretta a Lorenzo, richiesta approvazione/firma, allegato fattura/contratto/preventivo, scadenza esplicita, appuntamento da confermare.
5. ACTION se: scadenza esplicita ("entro il", "by", "deadline", "scade il", date in formato DD/MM o DD MMM).
6. VIP solo se l'utente lo ha specificato (whitelist vuota all'inizio).
7. INFO altrimenti.

TIE-BREAK:
- In dubbio tra PROMO e INFO -> INFO. Mai archiviare per errore.
- In dubbio tra INFO e ACTION -> classifica come ACTION ma imposta `confidence: low`. Non promuovere ad ACTION se Lorenzo e' solo admin delegato su account cliente — in quel caso e' INFO. Quando sei incerto, preferisci INFO a meno che l'azione non sia inequivocabilmente rivolta a Lorenzo in prima persona.
- Email di calendar invite (calendar-notification@google.com) -> INFO.
- Email di OTP / verifica / 2FA -> INFO.
- Email di sistema (GitHub, CI, status pages) -> INFO. Promuovere ad ACTION solo se richiede intervento esplicito.
- **Fatture / ricevute Klaviyo** (mittenti `klaviyo.com`, `*@klaviyo.com`, o Stripe `invoice+statements+...@stripe.com` con riferimento Klaviyo): SEMPRE PROMO. Lorenzo e' admin degli account Klaviyo dei clienti Mailift, ma le fatture le pagano i clienti, non lui. Quindi va archiviata e NON deve generare task. Stessa logica per altre piattaforme SaaS dove Lorenzo e' admin del cliente: se l'oggetto e' una fattura/ricevuta NON destinata a Mailift Srl come pagante, e' PROMO.
- **Notifiche sistema Klaviyo** (mittente `no-reply@klaviyo.com`): SEMPRE PROMO. Sono alert automatici su account clienti (es. integrazione Shopify disconnessa, warning deliverability) che Lorenzo vede come admin ma su cui non deve agire direttamente — l'azione spetta al cliente.
- **Notifiche sistema Stripe** (mittente `notifications@stripe.com`): PROMO se riguardano account/store di clienti Mailift (es. verifiche identita', payout, setup store). Lorenzo e' admin delegato, ma l'azione e' del cliente. Eccezione: se l'email riguarda esplicitamente Mailift Srl come entita' pagante/ricevente -> ACTION.
- **Vendor SaaS outreach / trial / onboarding** (es. Dropship `support@dropship.io`, Windsor.ai `*@mailing.windsor.ai` o `*@windsor.ai`, tool di analytics, tool di tracking): PROMO se si tratta di email commerciali, trial expiry, onboarding automatico, upsell. Non generano task.
- **Google sales outreach** (mittenti `*@xwf.google.com` o email Google di tipo commerciale/ads con oggetto su Google Ads, campagne, expert calls): PROMO. Lorenzo non gestisce direttamente account Google Ads dei clienti.
- **Vendor tecnici per setup account cliente** (es. Littledata, tool analytics/tracking che scrivono a Lorenzo per configurare un account di un cliente Mailift): INFO, non ACTION. Lorenzo non e' il punto di contatto tecnico per questi setup — l'azione spetta al cliente.

CAMPO actionable_title:
- Solo se categoria = ACTION o VIP. Altrimenti stringa vuota.
- In italiano, verbo all'infinito + oggetto. NON copiare l'oggetto raw.
- Esempi:
    - "Re: preventivo sito" -> "Rispondere a Marco con preventivo sito vetrina"
    - "Fattura allegata da pagare" -> "Pagare fattura n. X di fornitore Y"
    - "Conferma slot mercoledi" -> "Confermare slot meeting di mercoledi con Tizio"

CAMPO due_date:
- Estrai SOLO se la data e' esplicita ed univoca nell'email. Altrimenti null.
- Formato ISO YYYY-MM-DD.
- Usa la data odierna come base per "domani"/"tra una settimana".

CAMPO categoria_notion (per i task ACTION/VIP):
- Strategia    = decisioni alto livello, brief, pianificazione cliente
- Copy         = revisione testi, email marketing, contenuti
- Design       = mockup, creative, immagini, brand
- Tecnico      = integrazione, dominio, DNS, deliverability, plugin, API
- Reportistica = richieste di numeri, KPI, performance
- Altro        = fallback se non chiaro

CAMPO priorita_notion:
- Alta  = scadenza <= 48h o linguaggio urgente o cliente in escalation
- Media = default
- Bassa = "quando hai tempo", richieste informali

CAMPO suggested_cliente_query:
- Solo per email business che riguardano un cliente Mailift specifico
- Una stringa breve (nome cliente o dominio del cliente). Esempi: "bergamovini", "tre emme", "le rive"
- Stringa vuota se non c'e' un cliente identificabile

Sii preciso e veloce. NON inventare informazioni. Output sempre in italiano per i campi testuali."""


def _build_tool_schema() -> dict:
    return {
        "name": "report_email_classification",
        "description": "Restituisce la classificazione di un batch di email Gmail per il workflow di triage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Gmail message ID"},
                            "category": {"type": "string", "enum": ["PROMO", "INFO", "ACTION", "VIP"]},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                            "reason": {"type": "string"},
                            "actionable_title": {"type": "string", "description": "Titolo task in italiano (verbo + oggetto). Vuoto se non ACTION/VIP."},
                            "due_date": {"type": ["string", "null"], "description": "ISO YYYY-MM-DD o null"},
                            "categoria_notion": {"type": "string", "enum": ["Strategia", "Copy", "Design", "Tecnico", "Reportistica", "Altro"]},
                            "priorita_notion": {"type": "string", "enum": ["Alta", "Media", "Bassa"]},
                            "context_summary": {"type": "string", "description": "2-3 righe di contesto"},
                            "suggested_cliente_query": {"type": "string", "description": "Nome cliente o dominio per lookup nel DB Clienti. Vuoto se non applicabile."},
                        },
                        "required": ["id", "category", "confidence", "reason", "actionable_title", "categoria_notion", "priorita_notion", "context_summary", "suggested_cliente_query"],
                    },
                }
            },
            "required": ["results"],
        },
    }


def _classify_batch(client, model: str, emails: list[dict], account_label: str, today_iso: str, vip_list: list[str] | None) -> list[dict]:
    vip_block = ""
    if vip_list:
        vip_block = "\nWHITELIST VIP attiva (sempre VIP):\n" + "\n".join(f"- {v}" for v in vip_list) + "\n"

    compact = []
    for e in emails:
        compact.append({
            "id": e["id"],
            "from": e.get("from", ""),
            "subject": e.get("subject", ""),
            "date": e.get("date", ""),
            "list_unsubscribe": "yes" if e.get("list_unsubscribe") else "no",
            "has_attachments": e.get("has_attachments", False),
            "snippet": (e.get("snippet") or "")[:200],
            "body": (e.get("body") or "")[:800],
        })

    user_prompt = (
        f"Classifica queste {len(emails)} email ricevute sulla casella '{account_label}'. "
        f"Data odierna: {today_iso}.{vip_block}\n\n"
        f"Email:\n{json.dumps(compact, ensure_ascii=False, indent=2)}\n\n"
        "Chiama il tool report_email_classification con UNA entry per ogni email. "
        "Devi classificarle TUTTE, nessuna esclusa."
    )

    msg = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=[_build_tool_schema()],
        tool_choice={"type": "tool", "name": "report_email_classification"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_email_classification":
            return list(block.input.get("results", []))

    raise RuntimeError(f"Modello non ha chiamato il tool. Stop reason: {msg.stop_reason}")


def classify_emails(
    emails: list[dict],
    account_label: str,
    today_iso: str,
    vip_list: list[str] | None = None,
    batch_size: int = 25,
) -> list[dict]:
    """Classifica in batch da `batch_size`. Necessario perche' un singolo
    tool_use con >~30 email rischia di sforare max_tokens nel response."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # Modello dedicato (Haiku di default) — non usa ANTHROPIC_MODEL globale
    # perche' altri tool del progetto (autofatture) hanno bisogno di Opus.
    model = os.environ.get("INBOX_TRIAGE_MODEL") or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    if not emails:
        return []

    all_results: list[dict] = []
    for i in range(0, len(emails), batch_size):
        chunk = emails[i:i + batch_size]
        print(f"   classifico batch {i//batch_size + 1}/{(len(emails) + batch_size - 1)//batch_size} ({len(chunk)} email)…")
        results = _classify_batch(client, model, chunk, account_label, today_iso, vip_list)
        all_results.extend(results)
    return all_results
