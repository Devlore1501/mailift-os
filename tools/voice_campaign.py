"""voice_campaign.py — Campagne outbound dell'agente vocale (Vapi + GHL).

Orchestratore deterministico: pesca la coda contatti da GHL (solo opt-in),
lancia le chiamate via Vapi con pacing, attende gli esiti e riscrive
nota + tag esito sulla scheda contatto GHL.

Regole compliance (NON derogabili via CLI):
- Chiama SOLO contatti con tag `voice-optin` (consenso esplicito)
- Finestra chiamate: 10:00-18:00 Europe/Rome, lun-ven (bypass solo --force-window per test)
- Max 3 tentativi per contatto (contati sulle note "🤖 VOICE AGENT" in GHL)

Tag usati (vedi workflows/voice_agent.md):
- voice-optin       consenso a essere richiamati (gate, mai impostato da qui)
- da-richiamare     coda outbound (rimosso a esito terminale o max tentativi)
- esito-*           esito ultima chiamata (interessato/richiamare/non-interessato/non-risponde)

Usage:
    python tools/voice_campaign.py --dry-run                 # mostra coda, zero chiamate/scritture
    python tools/voice_campaign.py --limit 5                 # campagna reale, max 5 chiamate
    python tools/voice_campaign.py --assistant qualifica     # default: reengagement
    python tools/voice_campaign.py --contact-id XXX          # test su un singolo contatto
    python tools/voice_campaign.py --force-window            # ignora finestra oraria (solo test)
"""

from __future__ import annotations

import re
import sys
import time as _time
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import ghl_client as ghl
import vapi_client as vapi

TZ = ZoneInfo("Europe/Rome")

CONSENT_TAG = "voice-optin"
QUEUE_TAG = "da-richiamare"
NOTE_MARKER = "🤖 VOICE AGENT"

OUTCOME_TAGS = {
    "interessato": "esito-interessato",
    "richiamare": "esito-richiamare",
    "non_interessato": "esito-non-interessato",
    "non_risponde": "esito-non-risponde",
    "segreteria": "esito-non-risponde",  # segreteria telefonica = non raggiunto
}
# Esiti che chiudono la coda (rimuovono da-richiamare)
TERMINAL_OUTCOMES = {"interessato", "non_interessato"}

MAX_ATTEMPTS = 3
CALL_WINDOW = (time(10, 0), time(18, 0))  # lun-ven Europe/Rome
PACE_SECONDS = 20  # pausa tra un lancio e l'altro
CALL_TIMEOUT = 900  # attesa max esito singola chiamata


def within_call_window(now: datetime | None = None) -> bool:
    now = now or datetime.now(TZ)
    if now.weekday() >= 5:  # sab/dom
        return False
    return CALL_WINDOW[0] <= now.time() <= CALL_WINDOW[1]


def normalize_phone(phone: str) -> str:
    """Normalizza in E.164-ish per dedupe: solo cifre e +, prefisso IT se manca."""
    p = re.sub(r"[^\d+]", "", phone or "")
    if not p:
        return ""
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+"):
        p = "+39" + p.lstrip("0") if len(p) <= 10 else "+" + p
    return p


def count_attempts(contact_id: str) -> int:
    """Tentativi già fatti = note '🤖 VOICE AGENT' sulla scheda GHL.

    GHL è la fonte di verità: sopravvive a restart e conta anche le chiamate
    lanciate da altri percorsi che scrivono la stessa nota.
    """
    notes = ghl.list_notes(contact_id)
    return sum(1 for n in notes if (n.get("body") or "").startswith(NOTE_MARKER))


def fetch_queue(limit: int = 30) -> tuple[list[dict], list[str]]:
    """Coda contatti chiamabili + righe di log sugli esclusi.

    Query: tag AND [voice-optin, da-richiamare]. Poi filtra: telefono valido,
    dedupe per numero normalizzato, esiti terminali già presenti, max tentativi.
    """
    contacts = ghl.search_contacts_by_tags([CONSENT_TAG, QUEUE_TAG], limit=limit * 2)
    queue: list[dict] = []
    skipped: list[str] = []
    seen_phones: set[str] = set()

    for c in contacts:
        label = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or c.get("id", "?")
        tags = set(c.get("tags") or [])

        phone = normalize_phone(c.get("phone", ""))
        if not phone:
            skipped.append(f"{label}: telefono mancante")
            continue
        if phone in seen_phones:
            skipped.append(f"{label}: duplicato ({phone})")
            continue
        if tags & {OUTCOME_TAGS["interessato"], OUTCOME_TAGS["non_interessato"]}:
            skipped.append(f"{label}: esito terminale già presente")
            continue

        attempts = count_attempts(c["id"])
        if attempts >= MAX_ATTEMPTS:
            skipped.append(f"{label}: max tentativi raggiunti ({attempts}/{MAX_ATTEMPTS})")
            continue

        seen_phones.add(phone)
        queue.append({**c, "_phone": phone, "_attempts": attempts})
        if len(queue) >= limit:
            break

    return queue, skipped


def process_result(contact: dict, call: dict) -> str:
    """Scrive esito su GHL (nota + tag) e aggiorna la coda. Ritorna l'esito."""
    outcome = vapi.extract_outcome(call)
    esito = outcome["esito"]
    now_str = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    attempts = contact.get("_attempts", 0) + 1

    transcript = outcome["transcript"] or ""
    if len(transcript) > 1500:
        transcript = transcript[:1500] + "\n[...transcript troncato]"

    note_body = (
        f"{NOTE_MARKER} — {now_str}\n\n"
        f"Esito: {esito} (tentativo {attempts}/{MAX_ATTEMPTS})\n"
        f"Durata: {outcome['duration_s']}s | ended: {outcome['ended_reason']}\n"
        f"Appuntamento fissato: {outcome['structured'].get('appuntamento_fissato', 'n/d')}\n\n"
        f"RIEPILOGO:\n{outcome['summary'] or '(nessun riepilogo)'}\n\n"
        f"TRANSCRIPT:\n{transcript or '(nessun transcript)'}\n\n"
        f"call_id: {call.get('id', '?')}"
    )
    ghl.add_note(contact["id"], note_body)

    tag = OUTCOME_TAGS.get(esito)
    if tag:
        ghl.add_tags(contact["id"], [tag])

    if esito in TERMINAL_OUTCOMES or attempts >= MAX_ATTEMPTS:
        ghl.remove_tag(contact["id"], QUEUE_TAG)

    return esito


def run_campaign(
    assistant_key: str = "reengagement",
    limit: int = 10,
    dry_run: bool = False,
    force_window: bool = False,
    contact_id: str | None = None,
) -> dict:
    """Esegue la campagna. Ritorna un summary dict (riusabile da Telegram)."""
    print(f"\n{'='*60}")
    print(f"  VOICE CAMPAIGN — {datetime.now(TZ).strftime('%d %b %Y %H:%M')}")
    print(f"  Assistant: {assistant_key} | limit: {limit} | dry_run: {dry_run}")
    print(f"{'='*60}\n")

    if not dry_run and not force_window and not within_call_window():
        print("⛔ Fuori finestra chiamate (10:00-18:00 lun-ven Europe/Rome).")
        print("   Usa --force-window solo per test sul tuo numero.\n")
        return {"launched": 0, "blocked": "call_window"}

    if contact_id:
        c = ghl.get_contact(contact_id)
        tags = set(c.get("tags") or [])
        if CONSENT_TAG not in tags:
            print(f"⛔ Il contatto {contact_id} NON ha il tag `{CONSENT_TAG}` — non chiamabile.\n")
            return {"launched": 0, "blocked": "no_consent"}
        phone = normalize_phone(c.get("phone", ""))
        if not phone:
            print(f"⛔ Il contatto {contact_id} non ha un telefono valido.\n")
            return {"launched": 0, "blocked": "no_phone"}
        queue = [{**c, "_phone": phone, "_attempts": count_attempts(contact_id)}]
        skipped: list[str] = []
    else:
        queue, skipped = fetch_queue(limit=limit)

    print(f"📋 CODA: {len(queue)} contatti chiamabili")
    for c in queue:
        name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or "(senza nome)"
        print(f"  • {name} {c['_phone']} — tentativi: {c['_attempts']}/{MAX_ATTEMPTS}")
    if skipped:
        print(f"\n⏭  ESCLUSI ({len(skipped)}):")
        for s in skipped:
            print(f"  • {s}")
    print()

    if dry_run:
        print("🏜  DRY RUN — nessuna chiamata lanciata, nessuna scrittura su GHL.\n")
        return {"launched": 0, "queue": len(queue), "skipped": len(skipped), "dry_run": True}

    results: dict[str, int] = {}
    launched = 0
    for c in queue[:limit]:
        name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
        print(f"📞 Chiamo {name or c['_phone']} ...")
        try:
            call = vapi.create_call(
                c["_phone"],
                assistant_key,
                customer_name=name,
                metadata={"ghl_contact_id": c["id"], "campaign": assistant_key},
            )
            launched += 1
            call = vapi.wait_for_call(call["id"], timeout=CALL_TIMEOUT)
            esito = process_result(c, call)
            results[esito] = results.get(esito, 0) + 1
            print(f"   ✓ esito: {esito}")
        except (vapi.VapiError, ghl.GHLError) as exc:
            print(f"   ❌ errore: {exc}")
            results["errore"] = results.get("errore", 0) + 1
        _time.sleep(PACE_SECONDS)

    print(f"\n{'='*60}")
    print(f"  Lanciate: {launched} | Esiti: {results or '—'}")
    print(f"{'='*60}\n")
    return {"launched": launched, "results": results, "skipped": len(skipped)}


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    force_window = "--force-window" in args

    def flag_value(flag: str, default: str = "") -> str:
        if flag in args:
            i = args.index(flag)
            if i + 1 < len(args):
                return args[i + 1]
        return default

    assistant = flag_value("--assistant", "reengagement")
    if assistant not in ("qualifica", "reengagement"):
        print("--assistant deve essere: qualifica | reengagement")
        sys.exit(2)

    limit = 10
    try:
        limit = int(flag_value("--limit", "10"))
    except ValueError:
        pass

    contact_id = flag_value("--contact-id") or None

    try:
        run_campaign(
            assistant_key=assistant,
            limit=limit,
            dry_run=dry_run,
            force_window=force_window,
            contact_id=contact_id,
        )
    except (vapi.VapiError, ghl.GHLError) as exc:
        print(f"❌ errore: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
