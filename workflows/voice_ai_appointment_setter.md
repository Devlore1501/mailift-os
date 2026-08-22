# Voice AI Appointment Setter (Vapi → GHL)

## Obiettivo
Un agente vocale AI che chiama lead qualificati in Italia, si presenta come
assistente Mailift, verifica interesse e **fissa una discovery call**
direttamente sul calendario GHL — senza intervento manuale di Lorenzo per
la prenotazione. Sostituisce il Voice AI nativo di GHL, che al momento
consente outbound solo verso numeri USA (verificato luglio 2026).

## Perché non il Voice AI nativo di GHL
GHL Voice AI outbound calling è limitato a destinazioni USA. Esiste una
feature "Global Voice AI Outbound Calling" in beta da ottobre 2025, ma a
fine aprile 2026 non risultava confermata come rilasciata in produzione.
Soluzione: costruiamo l'agente su **Vapi** (supporta outbound
internazionale + numeri Twilio importati) e lo colleghiamo a GHL via
webhook per calendario e CRM.

## Architettura

```
Vapi (assistant + numero IT)
  │
  ├─ durante la call → POST /vapi/tool-calls  → tools/vapi_webhook_server.py
  │                                              → ghl_calendar_client (slot liberi, booking)
  │
  └─ fine call       → POST /vapi/server-events → tools/vapi_webhook_server.py
                                                   → ghl_client (nota + tag esito)
```

## Setup manuale richiesto (Lorenzo — non automatizzabile da qui)

Questi passaggi richiedono account/pagamento/documenti, non posso eseguirli
per te:

1. **Twilio**: crea account, compra un numero locale italiano (Voice).
   Per l'Italia serve un **Regulatory Bundle + Address** (documento
   identità/prova indirizzo) prima che il numero sia utilizzabile — segui
   [la guida GHL sui bundle regolatori](https://help.gohighlevel.com/support/solutions/articles/48001213216-regulatory-bundle-and-address-creation-for-sub-accounts)
   (stesso flusso vale per Twilio diretto).
2. **Vapi**: crea account su vapi.ai, poi *Phone Numbers → Import* per
   collegare il numero Twilio italiano. Annota il `phoneNumberId`.
3. **Vapi API Key**: Settings → API Keys → copia la Private Key.
4. **Hosting webhook**: `tools/vapi_webhook_server.py` deve essere
   raggiungibile via HTTPS pubblico.
   - Test/pilota: `ngrok http 8000` (gratuito, URL cambia ad ogni riavvio)
   - Produzione: deploy su Render/Railway/Fly.io (free tier sufficiente
     per basso volume) — dimmi quando vuoi procedere e ti preparo il deploy.
5. **Variabili da aggiungere a `.env`** (o `~/.secrets/mailift/.env`):
   ```
   VAPI_API_KEY=...
   GHL_CALENDAR_ID=...          # id del calendario "Discovery Call" su GHL
   VAPI_SERVER_SECRET=...       # stringa a piacere, per validare i webhook in arrivo
   ```
   Per trovare `GHL_CALENDAR_ID`: `python tools/ghl_calendar_client.py test`
   elenca tutti i calendari con relativo id.

## Compliance (obbligatoria, non opzionale)

- **Registro Pubblico delle Opposizioni (RPO)**: se il lead non è già
  cliente e non ha dato consenso esplicito al contatto telefonico, va
  verificato prima di chiamare. Non chiamare numeri iscritti al RPO senza
  consenso documentato.
- **Disclosure AI**: l'agente deve dichiararsi come assistente virtuale
  all'inizio della chiamata (Garante Privacy + AI Act art. 50). Il primo
  messaggio deve includerlo esplicitamente — vedi prompt sotto.
- **Fascia oraria**: chiamate outbound solo 09:00–19:00 Europe/Rome, mai
  festivi.
- **Opt-out immediato**: se il lead chiede di non essere ricontattato,
  l'agente deve chiuderla ed è compito del follow-up automatico taggare
  il contatto come "non contattare" su GHL (da aggiungere quando si
  automatizza la lista chiamate).

## Config assistant Vapi (riferimento)

Crea l'assistant via dashboard Vapi o `tools/vapi_client.py`
`create_assistant()` con una config di questo tipo:

```json
{
  "name": "Mailift Setter",
  "firstMessage": "Buongiorno, sono l'assistente virtuale di Mailift, la chiamo per conto di Lorenzo — ha un paio di minuti?",
  "model": {
    "provider": "anthropic",
    "model": "claude-sonnet-5",
    "systemPrompt": "Sei l'assistente vocale di Mailift, agenzia di email marketing per eCommerce DTC italiano. Il tuo unico obiettivo è fissare una discovery call di 20 minuti con Lorenzo per lead qualificati (eCommerce Shopify/Klaviyo, fatturato 25k-300k/mese). Dichiarati sempre come assistente AI se richiesto. Sii diretto, mai aggressivo, tono professionale ma caldo, in italiano. Se il lead non è interessato o non risponde ai criteri, ringrazia e chiudi la chiamata senza insistere. Se interessato, usa il tool check_availability per proporre 2-3 slot, poi book_appointment per confermare. Se il lead chiede di non essere ricontattato, conferma che non verrà più chiamato e chiudi."
  },
  "voice": { "provider": "11labs", "voiceId": "<voce italiana a scelta>" },
  "serverUrl": "https://<tuo-host>/vapi/tool-calls",
  "serverUrlSecret": "<VAPI_SERVER_SECRET>",
  "serverMessages": ["end-of-call-report"],
  "functions": [
    {
      "name": "check_availability",
      "description": "Controlla gli slot liberi sul calendario discovery call",
      "parameters": {
        "type": "object",
        "properties": { "days_ahead": { "type": "integer", "default": 5 } }
      }
    },
    {
      "name": "book_appointment",
      "description": "Fissa la discovery call sul calendario",
      "parameters": {
        "type": "object",
        "properties": {
          "contact_phone": { "type": "string" },
          "lead_name": { "type": "string" },
          "start_time": { "type": "string", "description": "ISO 8601" },
          "end_time": { "type": "string", "description": "ISO 8601" }
        },
        "required": ["contact_phone", "start_time", "end_time"]
      }
    }
  ]
}
```

Nota: il campo `serverUrl` per gli eventi di fine chiamata (`end-of-call-report`)
va impostato su `/vapi/server-events` — se Vapi non permette due server URL
diversi per tool-call ed eventi nella stessa config, verificare nella
dashboard la sezione "Server URL" separata dagli "Advanced" dell'assistant.

## Sequenza esecuzione

1. Lorenzo (o un workflow futuro di lead scoring) fornisce la lista lead
   da chiamare (telefono + nome, da GHL o CSV).
2. Per ciascun lead, verifica RPO/consenso e fascia oraria.
3. `tools/vapi_client.py create_outbound_call(assistant_id, phone_number_id, numero, metadata={"lead_name": ..., "ghl_contact_id": ...})`.
4. Durante la call, Vapi chiama `/vapi/tool-calls` per disponibilità e
   booking — gestito automaticamente da `tools/vapi_webhook_server.py`.
5. A fine call, `/vapi/server-events` scrive su GHL: nota con trascrizione
   + riepilogo, tag esito.
6. Lorenzo rivede in GHL i contatti taggati `setter-booked` e conferma
   personalmente eventuali appuntamenti critici prima della call.

## Convenzioni tag GHL (esito chiamata)

- `setter-booked` — appuntamento fissato
- `setter-callback` — lead interessato ma richiede di essere richiamato
- `setter-not-interested` — non interessato
- `setter-no-answer` — nessuna risposta / occupato
- `setter-voicemail` — finito in segreteria
- `setter-da-rivedere` — esito non chiaro dal payload, review manuale

## Edge case noti

- **Payload `end-of-call-report` non ancora verificato in produzione**:
  lo schema di `message.analysis` (summary/successEvaluation) non è
  documentato con precisione da Vapi. `tools/vapi_webhook_server.py`
  salva ogni payload grezzo in `.tmp/vapi_raw_payloads/` — ispezionarli
  dopo le prime chiamate di test e aggiustare `_extract_outcome()` di
  conseguenza.
- **Numero lead non trovato/malformato**: se `customer_number` manca dal
  payload, il webhook logga un warning e non scrive su GHL — non blocca
  il server.
- **Doppia prenotazione stesso slot**: `book_appointment` non fa retry né
  lock — se due chiamate concorrenti tentano lo stesso slot, GHL può
  rifiutare la seconda. A basso volume (poche chiamate/giorno) rischio
  trascurabile; da rivedere se si scala.
- **Contatto duplicato per formattazione telefono diversa** (`+39` vs
  `0039` vs locale): `find_or_create_contact` ora confronta solo le
  ultime 9 cifre — verificare che sia sufficiente quando si processano
  numeri fissi italiani (meno cifre significative del mobile).

## Verifica end-to-end (prima volta)

1. Setup manuale completo (sezione sopra), `.env` popolato.
2. `python tools/ghl_calendar_client.py test` → conferma calendario e slot letti.
3. `python tools/vapi_client.py test` → conferma numero importato visibile.
4. Avvia webhook locale: `uvicorn tools.vapi_webhook_server:app --reload --port 8000`
   + `ngrok http 8000`, incolla l'URL ngrok su Vapi.
5. Crea l'assistant su Vapi con la config di riferimento sopra.
6. **Chiamata di test verso il TUO numero** (mai un lead reale al primo giro):
   `python -c "from tools.vapi_client import create_outbound_call; print(create_outbound_call('<assistant_id>', '<phone_number_id>', '<tuo numero E.164>'))"`
7. Rispondi alla chiamata, verifica che il flusso booking funzioni, controlla
   `.tmp/vapi_raw_payloads/` per il payload reale di fine chiamata.
8. Verifica su GHL che nota + tag siano stati scritti correttamente.
9. Solo dopo un test pulito, passa a lead reali rispettando RPO e fascia oraria.
