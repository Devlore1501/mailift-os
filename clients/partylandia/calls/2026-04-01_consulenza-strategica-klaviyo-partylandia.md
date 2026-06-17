# Call: Strategia Marketing Automation e ESP – Partylandia

**Data:** [data call]
**Partecipanti:** Barbara, Roberto (Partylandia) | Lorenzo (Mailift)
**Fonte:** Fathom AI Summary

## Riassunto esecutivo
Definita strategia di marketing automation per Partylandia con selezione di Klaviyo come ESP (scartato Brevo). Implementati script di tracking, popup di segmentazione event-driven e integration plan con backend custom. Identificati colli di bottiglia nel flusso checkout bonifico e problemi critici sul sito spagnolo Prim Globos (zero conversioni).

## Decisioni prese
- **ESP selezionato:** Klaviyo (segmentazione event-driven, catalog feed, abandon tracking superiori)
- **Segmentazione utenti:** Implementata via popup branching (palloncini | gonfiabili | agenzia)
- **Integration approach:** Server-side da backend custom per eventi chiave + GTM dove opportuno
- **Priorità geografica:** Italia first; Prim Globos (sito spagnolo) in standby
- **Gestione checkout:** Ordini sospesi fino a pagamento confermato (no duplicate comms)

## Action items
### Lorenzo / Mailift
- [ ] Finalizzare mapping liste Brevo → Klaviyo (import)
- [ ] Validare script Klaviyo live e configurazione popup targeting
- [ ] Definire schema integration server-side (eventi chiave, touchpoint)
- [ ] Audit flusso checkout bonifico e logica di sospensione ordini
- [ ] Diagnosticare Prim Globos (analisi traduzione ES, pricing, UX checkout)
- [ ] Documentare playbook comunicazioni per ordini in sospeso

### Cliente (Partylandia)
- [ ] Confermare lista eventi chiave da tracciare via server-side
- [ ] Validare tassonomia segmentazione (palloncini/gonfiabili/agenzia)
- [ ] Fornire accesso analytics Prim Globos e feedback traduzione
- [ ] Testare flusso checkout bonifico in staging

## Contesto aggiornato cliente
- Partylandia gestisce segmentazione per 3 categorie prodotto principali (palloncini, gonfiabili, servizi agenzia)
- Usa Brevo attualmente → migrazione verso Klaviyo
- Accetta pagamenti via bonifico (processo con ordini sospesi)
- Portafoglio geografico: Italia (prioritaria) + Spagna (Prim Globos — in crisi)
- Necessita tracking event-driven sofisticato e abandon cart automation

## Segnali importanti
⚠️ **RISCHIO CRITICO:** Prim Globos (sito spagnolo) a zero conversioni — suspect: difetti traduzione, mismatch pricing, UX checkout
⚠️ **OPPORTUNITÀ:** Automazione event-driven Klaviyo potrebbe sbloccare re-engagement su gonfiabili (basso engagement?)
✅ **POSITIVO:** Team receptivo a integration complessa (server-side + GTM hybrid)

## Note operative
- Script Klaviyo già live e configurato
- Popup branching attivo (3 segmenti target)
- GTM da usare selettivamente (non per tutti gli eventi)
- **Vincolo critico:** Comunicazioni post-checkout bonifico devono gestire stato "ordine sospeso" (no reminder duplicate)
- Import Brevo in corso — coordinate mapping campi custom
- Server-side tracking richiede coordinamento con backend team cliente

---