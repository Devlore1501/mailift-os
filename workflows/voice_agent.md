# Voice Agent (Vapi + GHL) — inbound e outbound

## Obiettivo
Agente vocale AI completamente automatizzato per Mailift:
- **Inbound**: risponde al numero Mailift (+39), qualifica, prende messaggi,
  prenota discovery call sul calendario GHL.
- **Outbound singolo**: chiamata event-driven da workflow GHL (nuovo lead).
- **Outbound campagne**: code multi-chiamata (qualifica / riattivazione)
  orchestrate da `tools/voice_campaign.py`.

Architettura **zero server**: le integrazioni real-time passano dall'app Vapi
nel marketplace GHL (azioni + trigger end-of-call nei workflow) e dai tool GHL
nativi di Vapi (Get/Create Contact, Check Availability, Create Event). Il
codice Python gira in locale come gli altri tool.

## Variabili `.env` (in `~/.secrets/mailift/.env`)
- `VAPI_API_KEY` — API key privata Vapi
- `VAPI_PHONE_NUMBER_ID` — numero IT importato da Twilio
- `VAPI_ASSISTANT_INBOUND_ID` / `VAPI_ASSISTANT_QUALIFICA_ID` / `VAPI_ASSISTANT_REENGAGEMENT_ID`
- (esistenti) `GHL_API_KEY`, `GHL_LOCATION_ID`

## Tool Python
- [tools/vapi_client.py](../tools/vapi_client.py) — chiamate, batch, esiti (`test` CLI read-only)
- [tools/voice_campaign.py](../tools/voice_campaign.py) — campagne outbound (default consigliato: `--dry-run` prima di ogni run reale)
- [tools/ghl_client.py](../tools/ghl_client.py) — `search_contacts_by_tags` per la coda
- [tools/reengagement_radar.py](../tools/reengagement_radar.py) — `--ghl --voice` alimenta la coda

## Prompt assistant
Source of truth in [knowledge/voice/](../knowledge/voice/README.md) — sync
manuale nel dashboard Vapi dopo ogni modifica.

## Tassonomia tag GHL
| Tag | Significato | Chi lo imposta |
|---|---|---|
| `voice-optin` | Consenso a essere richiamati. **Gate obbligatorio per ogni outbound.** | Form/automazioni GHL, MAI i tool voce |
| `da-richiamare` | In coda outbound | Radar `--voice`, workflow GHL, manuale |
| `chiama-subito` | Trigger outbound immediato (workflow GHL) | Manuale/automazioni |
| `esito-interessato` | Ha fissato/vuole la call | `voice_campaign.py` / workflow post-call |
| `esito-richiamare` | Da richiamare più avanti | idem |
| `esito-non-interessato` | Chiuso, non ricontattare via voce | idem |
| `esito-non-risponde` | Non risponde / segreteria | idem |
| `chiamata-inbound-voice` | Ha chiamato lui il numero Mailift | workflow GHL inbound |

## Regole compliance (NON derogabili)
1. Outbound SOLO verso contatti con `voice-optin` (GDPR + Registro Opposizioni:
   niente cold calling automatizzato).
2. Finestra chiamate: **10:00-18:00 Europe/Rome, lun-ven** (`--force-window`
   solo per test sul numero di Lorenzo).
3. **Max 3 tentativi** per contatto (contati sulle note `🤖 VOICE AGENT` in GHL).
4. Mai chiamare clienti retainer o ex clienti con le campagne (il radar già
   li esclude; per code manuali, verificare).
5. Se il lead chiede la rimozione: rimuovere `voice-optin` e `da-richiamare`
   dalla scheda, subito.
6. Campagne MAI da cron non presidiato in v1: si lanciano a richiesta
   (CLI o Telegram), Lorenzo presente.

## Quando usare cosa
| Scenario | Strumento |
|---|---|
| Lead compila il form → chiamalo entro 5 min | Workflow GHL `Voice — Outbound singolo` (tag `chiama-subito`) |
| Coda riattivazione mensile | `reengagement_radar.py --ghl --voice` poi `voice_campaign.py` |
| Coda qualifica (lead vecchi non lavorati) | Tag manuale `da-richiamare` + `voice_campaign.py --assistant qualifica` |
| Report chiamate di ieri | `vapi_client.py list` o job `voice_campaign_report` |

## Esecuzione campagna (sequenza)
1. `python tools/voice_campaign.py --dry-run` → rivedi coda ed esclusi.
2. Conferma di Lorenzo (le chiamate sono reali e a pagamento).
3. `python tools/voice_campaign.py --limit N [--assistant qualifica]`.
4. Il tool per ogni chiamata: lancia → attende esito → scrive nota
   `🤖 VOICE AGENT` + tag `esito-*` → rimuove `da-richiamare` se terminale.
5. Riporta il summary (lanciate/esiti) in chat.

## Setup esterno (one-time, riferimento)
1. Numero italiano +39 — opzioni in ordine di convenienza:
   - **Telnyx** (consigliato): numero geografico a pochi €/mese + KYC IT,
     collegato a Vapi via BYO SIP trunk (FQDN `sip.vapi.ai`). Testare subito
     una chiamata reale (segnalati intoppi occasionali Telnyx+Vapi in community).
   - Provider VoIP italiano (VoipVoice, Messagenet, DIDWW...) via BYO SIP trunk;
     se Lorenzo ha già un numero VoIP con credenziali SIP, si collega quello.
   - Twilio: per l'Italia vende solo mobile/toll-free (~90 €/mese) — sconsigliato,
     usare solo se serve l'import nativo. Numeri SIM mobili (TIM ecc.) non sono
     collegabili: eventualmente portabilità verso Telnyx.
   ⚠️ MAI numero US con caller ID italiano "sovrapposto": bloccato dal filtro
   anti-spoofing AGCOM (fissi dal 08/2025, mobili dal 11/2025), oltre che illecito
   se il numero non è tuo.
2. Vapi: collega il numero (import Twilio o BYO SIP trunk) → 3 assistant (prompt da `knowledge/voice/`)
   → analysisPlan con lo schema in `knowledge/voice/README.md` → tool GHL
   nativi (OAuth + `calendarId`).
3. GHL: app Vapi dal marketplace + 3 workflow (`Voice — Inbound post-call`,
   `Voice — Outbound singolo`, `Voice — Outbound post-call`).
   ⚠️ Lezioni audit CAPI: mai azioni nel ramo ELSE, mai test code attivi.
4. ⚠️ Anti-spoofing AGCOM (delibere 106/25 e 271/25/CONS): usare SOLO il
   numero italiano vero importato; mai caller ID "mascherati". Al primo test
   verificare che le chiamate arrivino ai cellulari italiani.

## Edge case noti
- **Segreteria telefonica**: l'assistant riaggancia senza lasciare messaggi;
  esito `non_risponde`, il contatto resta in coda (fino a 3 tentativi).
- **Numero errato / persona diversa**: esito `non_interessato` con nota
  "numero errato" → verificare il campo phone sulla scheda GHL.
- **Richiesta di rimozione**: l'assistant lo segna nelle note → rimuovere
  `voice-optin` + `da-richiamare` a mano (o workflow GHL dedicato).
- **Chiamata caduta / errore Vapi**: il tentativo conta comunque (nota
  scritta con ended_reason); ripartire dal `--dry-run`.
- **Lead già cliente**: non deve succedere (filtri a monte); se succede,
  l'assistant prende il messaggio come per un cliente e Lorenzo richiamerà.

## Verifica end-to-end (prima volta)
1. `python tools/vapi_client.py test` — elenca numero +39 e 3 assistant.
2. Contatto GHL di test con il numero di Lorenzo + tag `voice-optin` + `da-richiamare`.
3. `python tools/vapi_client.py call <numero-lorenzo> --assistant qualifica`
   → parlare con l'agente in italiano → `status <call_id>` deve mostrare
   transcript, summary ed esito strutturato.
4. `python tools/voice_campaign.py --dry-run` — coda = solo il contatto test.
5. `python tools/voice_campaign.py --contact-id <test> --limit 1 --force-window`
   → su GHL: nota `🤖 VOICE AGENT` + tag esito; `da-richiamare` rimosso se terminale.
6. Inbound: chiamare il +39 da cellulare → workflow post-call crea nota/tag;
   provare la prenotazione (Check Availability + Create Event).
7. Ripetere il punto 5 fino a verificare il cap dei 3 tentativi.

## Apprendimenti
(da popolare dopo i primi run: esiti mal classificati, frasi che confondono
l'assistant, orari con answer rate migliore, ecc.)
