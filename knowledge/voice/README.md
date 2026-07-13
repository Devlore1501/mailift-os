# Prompt agente vocale (Vapi)

Questi file sono la **source of truth** dei prompt degli assistant Vapi.
In v1 il sync è **manuale**: dopo ogni modifica, copia-incolla il prompt nel
dashboard Vapi (Assistants → system prompt). Un subcommand `push-prompt` in
`tools/vapi_client.py` è previsto per v2.

| File | Assistant Vapi | Uso |
|---|---|---|
| [inbound_segretaria.md](inbound_segretaria.md) | `Segretaria Inbound Mailift` | Risponde alle chiamate in entrata sul numero Mailift |
| [outbound_qualifica.md](outbound_qualifica.md) | `Qualifica Lead` | Outbound: qualifica lead + fissa discovery call |
| [outbound_riattivazione.md](outbound_riattivazione.md) | `Riattivazione Lead` | Outbound: re-engagement lead freddi |

## Configurazione comune (tutti gli assistant)

- **Lingua**: italiano.
- **Voce**: ElevenLabs, modello multilingual, voce italiana professionale.
- **Transcriber**: Deepgram nova-2/nova-3 con `language: it` (fallback Whisper).
- **LLM**: GPT-4o o Claude, temperatura bassa (0.3-0.4).
- **Tool GHL nativi** (su Inbound e Qualifica): Get Contact, Create Contact,
  Check Availability, Create Event — richiedono OAuth verso la location GHL
  e il `calendarId` della discovery call (GHL → Settings → Calendars).

## analysisPlan (identico per i 3 assistant)

- `summaryPrompt` (in italiano): "Riassumi la chiamata in max 6 righe: chi era,
  cosa voleva/come ha reagito, pain point emersi, next step concordato."
- `structuredDataSchema`:

```json
{
  "type": "object",
  "properties": {
    "esito": {
      "type": "string",
      "enum": ["interessato", "richiamare", "non_interessato", "segreteria"]
    },
    "appuntamento_fissato": { "type": "boolean" },
    "note": { "type": "string" }
  },
  "required": ["esito", "appuntamento_fissato"]
}
```

Questo schema è consumato da `tools/vapi_client.py::extract_outcome` e dai
workflow GHL post-call. **Non cambiare l'enum senza aggiornare
`tools/voice_campaign.py::OUTCOME_TAGS`.**

## Tassonomia tag GHL

Vedi [workflows/voice_agent.md](../../workflows/voice_agent.md):
`voice-optin`, `da-richiamare`, `esito-interessato`, `esito-richiamare`,
`esito-non-interessato`, `esito-non-risponde`, `chiamata-inbound-voice`.
