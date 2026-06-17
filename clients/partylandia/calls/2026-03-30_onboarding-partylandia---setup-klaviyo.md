# Call: Onboarding Partylandia – Checkout e Migrazione Klaviyo

**Data:** 2026-03-30
**Partecipanti:** Barbara Turcatel (Partylandia), Roberto (dev Partylandia), Lorenzo (Mailift)
**Fonte:** Fathom AI Summary

## Riassunto esecutivo
Avviato onboarding Partylandia con focus su risoluzione anomalia checkout (ordini confermati senza pagamento). Migrazione email platform da Brevo a Klaviyo in corso. Definito schema di segmentazione clienti (palloncini vs gonfiabili) e configurazione popup con branching logic per agenzie. Tracking script Klaviyo installato e validato; integrazione server-side pianificata per novembre.

## Decisioni prese
- Installazione e verifica Klaviyo tracking script completata
- Segmentazione clienti per categoria prodotto (palloncini / gonfiabili)
- Percorso popup dedicato per agenzie (branching terzo)
- Soppressione flussi recovery marketing quando metodo pagamento = bonifico
- Rollout geografico: Italia prima, Spagna dopo

## Action items
### Lorenzo / Mailift
- [ ] Configurare integrazione server-side per eventi (Viewed Product, Added to Cart, Checkout, Purchase, Bonifico Paid)
- [ ] Implementare logica di soppressione recovery marketing per pagamenti bonifico
- [ ] Validare segmentazione clienti in Klaviyo (palloncini vs gonfiabili)
- [ ] Coordinare setup popup branching per agenzie
- [ ] Pianificare estensione a mercato Spagna post-Italia

### Cliente
- [ ] Installare e validare tracking script Klaviyo (verificato ✓)
- [ ] Fornire dettagli tecnici checkout per debug anomalia ordini
- [ ] Confermare mappatura clienti per segmentazione prodotto

## Contesto aggiornato cliente
- **Partylandia** – retailer articoli per feste (palloncini, gonfiabili)
- Anomalia critica: checkout confirma ordine ma non elabora pagamento
- Transizione email: Brevo → Klaviyo
- Clienti: retail B2C + agenzie (percorso differenziato)
- Pagamenti: bonifico richiede soppressione automation recovery

## Segnali importanti
- **Rischio operativo**: Anomalia checkout impatta fatturato — priorità debug
- **Opportunità**: Segmentazione prodotto consente upsell e retention mirati
- **Flag strategico**: Metodologia bonifico richiede logic automation ad-hoc (non standard)
- **Espansione**: Piano Spagna già in roadmap — preparare scalabilità

## Note operative
- Tracking script Klaviyo: **installato e verificato** ✓
- Integrazione server-side: programmata per prossima fase
- Popup branching: 3 percorsi (B2C palloncini, B2C gonfiabili, agenzie)
- Vincolo pagamento: bonifico non riceve email recovery (soppressione obbligatoria)
- Rollout geografico: MVP Italia, successivo Spain expansion