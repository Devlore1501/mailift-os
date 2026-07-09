# La Fenice

**Contatto principale:** Alice Gattolin (marketing manager)
**Owner:** Francesco Conton (fisioterapista/owner, accesso Aruba)
**Business:** Centro fisioterapia — 3 sedi (Mestre, Padova, Treviso)
**Stack:** Delera (CRM), Meta Ads, Aruba (dominio), email automation
**Stato:** Retainer attivo
**MRR attuale:** da confermare (chiedi a Lorenzo)

## Contesto business
Centro fisioterapia multi-sede con ~15 fisioterapisti. Funnel: lead da Meta → chatbot → chiamata segretaria → prima valutazione (€75) → trattamento (10 sessioni ~1-2 mesi). Conversioni: 30-35% lead→appuntamento, 60% prima valutazione→trattamento. Spesa Meta: ~€15k/mese su 6-9 campagne (3 per sede). Costo per lead: €30-40.

## Ultime decisioni
_Ultima call: [2026-07-03](calls/2026-07-03_analisi-performance-campagne-email-la-fenice-e-ott.md)_

- Reinvio delle email di Padova oggi e di Treviso domani, per evitare il blocco da volume di invio.
- Utilizzo della modalità **drip** (invio scaglionato durante la giornata) invece dell'invio in blocco.
- Sostituzione del processo di risposta in chat con un **form da compilare** (nome, telefono, problematiche + allegato radiografie/referti in PDF).
- Inserimento di un **filtro per zona geografica** come primo step: lead vicini a Padova/Treviso/Mestre → percorso verso analisi gratuita/visita; fuori zona → accesso a corsi.
- I lead che rispondono e completano il percorso vanno **contattati telefonicamente** (le persone non ricontrollano le mail con frequenza).
- Test del mittente: firmare le email come "La Fenice Centro Riabilitativo" invece che come team/automazione.
- Mantenere la frequenza di **una mail a settimana**.


## Prossimi step
### Lorenzo / Mailift
- [ ] Preparare e inviare il form di screening nel pomeriggio, con tutte le info (nome, telefono, problematiche, allegato PDF)
- [ ] Reinviare le mail di Padova oggi e Treviso domani in modalità drip
- [ ] Verificare/risolvere il problema di tracciamento risposte su Mestre (probabile causa: indirizzo di risposta diverso dall'indirizzo di invio)
- [ ] Verificare il limite di invio che ha causato i fallimenti su Padova (2.393 processate, 2.370 fallite)
- [ ] Completare e testare l'integrazione della funzione AI di classificazione risposte in chat
- [ ] Impostare il filtro per zona come primo campo del percorso lead
- [ ] Valutare protocollo PDF con soluzioni/ipotesi in base alle risposte (fase successiva)

### Cliente
- [ ] Francesco/Alice: verificare i lead che hanno completato il percorso e che sono da richiamare
- [ ] Effettuare screening delle documentazioni ricevute e fissare gli appuntamenti
- [ ] Confermare l'approccio del form + chiamata telefonica


## Note operative
- Sequenze segmentate per zona (Mestre/Padova/Treviso) e per problema specifico
- 3 siti separati (uno per sede + quello di Francesco) su stesso provider
- Nessun tracciamento email→conversione attuale: priorità da risolvere con form tracciato
- Delera usato in modalità semplificata: calendari generici (controlli, terapia, prima valutazione)
