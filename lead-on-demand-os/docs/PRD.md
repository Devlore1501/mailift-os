# PRD – Lead on Demand OS

Versione: 1.0
Prodotto: Lead on Demand OS
Tipologia: SaaS interno + portale clienti
Settore iniziale: fotovoltaico
Estendibile in futuro ad altri verticali Pay per Lead

Principio architetturale: Lead on Demand OS è la fonte principale dei dati. GoHighLevel è il layer operativo per chiamate, SMS, WhatsApp, workflow, pipeline e appuntamenti. Nessuna logica commerciale (pacchetti, credito, assegnazioni, territori, esclusività, replacement, pricing, marginalità) vive in GHL.

Stato di implementazione della prima release (sezioni 1–48): vedi la tabella in fondo.

## 1. Visione del prodotto

Lead on Demand OS è il sistema centrale per gestire un'attività Pay per Lead con più clienti contemporaneamente. Il software permette di acquisire lead da landing page, Meta Ads, Google Ads, form e API; classificarli e prequalificarli; assegnarli automaticamente al cliente corretto; gestire clienti con pacchetti prepagati; controllare lead acquistati, consegnati, scartati e sostituiti; impedire la consegna oltre il volume acquistato; gestire territori ed esclusività; inviare i lead a GoHighLevel e riceverne gli aggiornamenti; gestire appuntamenti; misurare performance e marginalità; dare al cliente finale un portale con i propri lead; gestire richieste di sostituzione. L'architettura deve reggere il passaggio da pochi clienti a decine o centinaia di buyer.

## 2. Architettura

ACQUISIZIONE → LEAD ON DEMAND OS → ROUTING ENGINE → TEAM LEAD ON DEMAND / GHL → QUALIFICA → CLIENTE / INSTALLATORE → APPUNTAMENTO → ESITO COMMERCIALE → LEAD ON DEMAND OS

## 3. Utenti e ruoli

Super Admin: tutto, inclusi costi, marginalità, integrazioni, rettifiche credito. Manager: lead, operatori, performance, assegnazioni, approvazioni, replacement; non vede necessariamente i dati finanziari. Operatore: solo i lead assegnati o nelle code autorizzate; chiama, qualifica, annota, cambia stato, fissa appuntamenti, programma richiamate; non tocca pacchetti, pricing, routing, marginalità. Cliente: solo i propri lead, appuntamenti, pacchetti, residui, storico, statistiche, replacement, documenti; mai altri clienti, costi advertising, margini, lead non assegnati, logiche di routing.

## 4. Dashboard amministrativa

KPI: lead generati oggi e nel mese, da contattare, qualificati, non qualificati, consegnati, in review, replacement richiesti e approvati, appuntamenti fissati, show, no-show, clienti attivi, pacchetti attivi, lead ancora da consegnare, revenue venduta, revenue riconosciuta sui lead consegnati, costo acquisizione, margine lordo, margine per lead. Filtri per periodo, cliente, provincia, regione, campagna, fonte, operatore, tipologia lead, stato.

## 5. Gestione clienti

Scheda con dati aziendali (ragione sociale, nome commerciale, P.IVA, referente, telefono, email, indirizzo, regione, province e CAP serviti, sito), configurazione commerciale (tipologia residenziale/aziende/entrambi; offerta lead qualificato digitalmente, lead + prequalifica telefonica, lead + appuntamento; prezzo per lead; lead acquistati e residui; date; stato ACTIVE, PAUSED, OUT_OF_CREDIT, CANCELLED) e configurazione operativa (GHL Location ID, Pipeline ID, Calendar ID, webhook URL, CRM esterno, email e telefono notifiche, responsabile commerciale).

## 6. Pacchetti

Ogni acquisto è un oggetto autonomo (codice tipo PV-2026-00031, prodotto, quantità, prezzo unitario, totale, pagamento, consegnati, residui, replacement, stato). Stati: DRAFT, AWAITING_PAYMENT, ACTIVE, LOW_BALANCE, COMPLETED, PAUSED, EXPIRED, CANCELLED. Un lead scala il credito solo quando raggiunge lo stato "consegnato". Replacement approvato: +1. Ogni movimento è nel ledger immutabile.

## 7. Lead ledger

Tabella LEAD_CREDIT_TRANSACTIONS (transaction_id, client_id, package_id, lead_id, type, quantity, reason, created_at, created_by). Tipi: PURCHASE +N, DELIVERY -1, REPLACEMENT +1, MANUAL_ADJUSTMENT +/-. Il saldo non dipende da un campo modificabile.

## 8. Lead

ID univoco; dati personali (nome, cognome, telefono, email, indirizzo, comune, CAP, provincia, regione); tracking marketing (source, medium, campaign, ad set, ad, creative, landing page, UTM, click ID, timestamp, costo attribuito); dati fotovoltaico residenziale (proprietario, tipo immobile, tetto disponibile e di proprietà, bolletta, kWh, persone, pompa di calore, auto elettrica, accumulo, motivazione, tempistica, decision maker, preventivi già richiesti); dati fotovoltaico aziendale (ragione sociale, proprietà capannone, consumo annuo, superficie tetto, attività, comune, sedi, accumulo, tempistica, referente decisionale).

## 9. Stati del lead

NEW, VALIDATING, TO_CONTACT, ATTEMPT_1, ATTEMPT_2, ATTEMPT_3, CALLBACK, CONTACTED, QUALIFYING, QUALIFIED, NOT_QUALIFIED, WAITING_ASSIGNMENT, ASSIGNED, APPOINTMENT_BOOKED, DELIVERED, REPLACEMENT_REQUESTED, REPLACEMENT_APPROVED, REPLACEMENT_REJECTED, CLOSED_WON, CLOSED_LOST. Ogni cambio salva data, ora, utente, stato precedente, nuovo stato, motivazione.

## 10. Routing engine

Regole per geografia (nazione, regione, provincia, comune, CAP, raggio), tipologia (residenziale, aziendale, prodotto, servizio), qualificazione (proprietario, consumo minimo, spesa minima, tempistica, accumulo, decision maker, custom field) e commerciali (cliente attivo, credito, limiti giornalieri/settimanali/mensili, esclusività).

## 11. Esclusività territoriale

Provincia, comune o CAP esclusivi oppure territorio condiviso. Con un'esclusiva attiva nessun altro cliente riceve lead qualificati di quel territorio. I conflitti vengono rilevati in configurazione: "Impossibile assegnare Vicenza a Cliente B. Il territorio è attualmente assegnato in esclusiva a Cliente A."

## 12. Lead cap

Limiti per cliente (es. 3/giorno, 15/settimana, 40/mese). Raggiunto il limite il Routing Engine sospende temporaneamente il cliente.

## 13. Coda di assegnazione

Lead valido senza cliente disponibile: WAITING_ASSIGNMENT, con motivo (territorio scoperto, senza credito, in pausa, cap raggiunto, nessun cliente compatibile). Dato visibile commercialmente: identifica domanda senza buyer.

## 14. Duplicate detection

Controllo su telefono, email, combinazione indirizzo + cognome. Finestra configurabile (30, 60, 90, 180 giorni, custom). Esiti UNIQUE, DUPLICATE, POSSIBLE_DUPLICATE. I duplicati non scalano il pacchetto.

## 15. Prequalifica

Script guidato con domande a salti; questionario configurabile senza codice; ogni cliente può avere criteri obbligatori, preferenziali, di esclusione.

## 16. Qualification score

Punteggio per regola (es. proprietario +20, consumo +20, installazione <3 mesi +20, decision maker +15, tetto +15, accumulo +5, telefono verificato +5), categorie HOT, QUALIFIED, REVIEW, NOT_QUALIFIED. Configurabile per verticale e cliente; non sostituisce i criteri obbligatori.

## 17. Integrazione GoHighLevel

Bidirezionale. Verso GHL: creare/aggiornare contatto e opportunità, tag, custom field, owner, dati di qualifica, workflow, appuntamento. Da GHL: contatto e opportunità aggiornati, stato pipeline, appuntamento creato/cancellato, show, no-show, vendita, perdita. Eventi salvati in un log.

## 18. Mapping GHL

Ogni cliente ha un mapping campo Lead on Demand → campo GHL, modificabile da pannello Admin.

## 19. Calendari

Uno o più calendari per cliente (telefonata, video call, sopralluogo, consulenza) con provider, id, durata, timezone, buffer, anticipo minimo, disponibilità. L'operatore vede gli slot disponibili e conferma. (Fase 2)

## 20. Appointment management

Stati BOOKED, CONFIRMED, CANCELLED, RESCHEDULED, SHOW, NO_SHOW, COMPLETED. Collegato a lead, cliente, operatore, calendario, pacchetto.

## 21. Reminder

Delegati a GHL con template configurabile. (Fase 2)

## 22–24. Replacement, workflow e SLA

Il cliente richiede la sostituzione con motivo (numero inesistente, mai interessato, fuori territorio, duplicato, non proprietario, dati falsi, criteri non rispettati, altro), nota, allegati. Flusso REPLACEMENT_REQUESTED → APPROVED/REJECTED; se approvato credito +1, lead marcato REPLACED e mantenuto in storico. SLA per cliente/pacchetto (24h, 48h, 72h, 7 giorni, custom); oltre il termine "Periodo disponibile per richiedere la sostituzione terminato", con override manuale Admin.

## 25–27. Portale cliente, esito commerciale, analytics cliente

Dashboard con pacchetto (acquistati, consegnati, residui, replacement), appuntamenti, show, no-show; tabella lead; scheda con risposte, note, appuntamento, timeline, richiesta replacement. Esito: CONTATTATO, APPUNTAMENTO, SOPRALLUOGO ESEGUITO, PREVENTIVO INVIATO, VENDUTO (valore, data, margine, prodotto), PERSO (motivo). Analytics: ricevuti, contattati, appuntamenti, show, preventivi, vendite, valore, costo lead, costo per cliente acquisito, revenue/costo; distinzione tra metriche confermate e dati mancanti.

## 28–31. Analytics Lead on Demand, unit economics, campaign economics, revenue recognition

Per cliente: revenue, lead venduti, costi attribuiti, gross profit e margin, costo e prezzo medio lead, replacement/qualification/appointment/show/close rate. Per campagna: spend, lead raw, CPL raw, qualificati, costo lead qualificato, venduti, revenue, replacement, gross profit. Cash collected distinto da lead revenue delivered e remaining delivery obligation.

## 32–34. Notifiche, alert pacchetto, pipeline rinnovo

Eventi: nuovo lead, qualificato, senza buyer, pacchetto quasi terminato/terminato, replacement richiesto, replacement rate anomalo, cliente senza attività, appuntamento, no-show, vendita. Canali in-app, email, Slack, WhatsApp. Soglie standard: 5 residui warning, 3 alert commerciale, 0 stop routing. Rinnovo: RENEWAL_REQUIRED con stati TO_CONTACT, CONTACTED, PROPOSAL, PAID, LOST; al pagamento nasce il nuovo pacchetto.

## 35. Billing

MVP: registrazione manuale del pagamento. Poi Stripe. Il routing non parte prima dell'attivazione del pacchetto, salvo override Admin.

## 36. Audit log

Ogni azione importante è registrata; nessun evento finanziario o di credito è modificabile senza traccia.

## 37–38. Data model

users, clients, client_users, packages, package_transactions, leads, lead_sources, lead_answers, lead_status_history, qualification_templates, qualification_rules, territories, routing_rules, lead_assignments, appointments, replacement_requests, campaigns, marketing_costs, sales_outcomes, integrations, ghl_mappings, webhook_events, notifications, audit_logs. Relazioni: client 1:N packages e territories; package 1:N assignments; lead 1:N status history, assignments, appointments, replacement requests; campaign 1:N leads.

## 39–40. API e webhook

API-first con autenticazione, autorizzazione e logging: POST/GET/PATCH /leads, /clients, /packages, POST /routing/evaluate, /leads/{id}/qualify, /assign, /deliver, /replacement, /appointments, /webhooks/ghl, GET /analytics. Eventi in uscita: lead.created, lead.qualified, lead.assigned, lead.delivered, lead.rejected, lead.replacement_requested, lead.replaced, package.low_balance, package.completed, appointment.booked, appointment.show, appointment.no_show, sale.won, sale.lost.

## 41. Privacy e sicurezza

Autenticazione sicura, RBAC, segregazione dati tra clienti, log accessi, cifratura in transito, cancellazione/anonimizzazione, retention configurabile, consenso e provenienza registrabili, export, backup, audit log, procedure GDPR. Il portale cliente non deve mai esporre dati di un altro cliente.

## 42–47. UX operatore, Admin, cliente, ricerca, filtri, export

Schermata chiamata: sinistra dati lead, centro script dinamico, destra risposte e note, bottom bar NON RISPONDE / RICHIAMA / QUALIFICATO / NON QUALIFICATO / FISSA APPUNTAMENTO. Sidebar Admin: Dashboard, Lead, Clienti, Pacchetti, Routing, Territori, Appuntamenti, Replacement, Campagne, Analytics, Team, Integrazioni, Impostazioni. Sidebar cliente: Dashboard, Lead, Appuntamenti, Pacchetto, Statistiche, Supporto. Ricerca globale (nome, telefono normalizzato, email, ID, cliente, azienda, provincia). Filtri combinabili. Export CSV/XLSX per Admin, solo dati propri per il cliente.

## 48. MVP

Autenticazione, clienti, pacchetti, lead, territori, criteri di qualificazione, pipeline lead, routing, credito pacchetto, ledger, duplicate detection, integrazione GHL, prequalifica operatore, assegnazione, consegna, replacement, dashboard Admin, portale cliente essenziale, audit log, notifiche pacchetto.

## 49–51. Fuori MVP, fase 2, fase 3

Fuori MVP: CRM completo, dialer, WhatsApp, email marketing, page builder, gestione advertising, fatturazione completa, app mobile, AI voice, telefonia, video call, chat interna. Fase 2: calendari multipli, booking sopralluoghi, Google/GHL Calendar, reminder, analytics avanzate, campaign economics, ROI cliente, Stripe, rinnovi, lead cap, round robin, routing avanzato, portale completo. Fase 3: multi-verticale, white label, AI scoring, trascrizione e analisi chiamate, controllo qualità operatori, forecast, pricing dinamico, marketplace buyer, ping/post, altri CRM.

## 52–56. Architettura tecnica, multi-tenancy, idempotenza, error handling, metriche

Next.js/React, Node.js TypeScript, PostgreSQL, ORM, auth con RBAC e organizzazioni, coda, storage S3, Vercel + backend separato, monitoring. Multi-tenant dall'inizio: ogni record cliente porta client_id e le query del portale sono limitate al tenant autenticato lato server. Webhook idempotenti (provider, external_event_id, received_at, processed_at, status, payload). Invio a GHL fallito: DELIVERY_FAILED, retry, alert Admin. Metriche: webhook failure rate, GHL sync failure, routing failure, latenza, duplicati, booking failure, API latency, backlog coda.

## 57. Definition of Done MVP

Un lead compila il form → entra → controllo duplicati → territorio → coda team → operatore chiama → qualificazione → criteri superati → Routing Engine trova il cliente → verifica pacchetto → assegna → scala 1 credito → invia a GHL → il cliente lo vede nel portale → tutto registrato → se contestato, replacement → se approvato, +1 credito → a pacchetto zero il routing verso quel pacchetto si blocca. Senza Excel né gestione manuale parallela.

## 58. Caso reale

Rossi Impianti: 20 lead a 200 euro, Vicenza, fotovoltaico residenziale. CREDIT +20. Arriva Mario Rossi (Vicenza, proprietario, villetta, 180 euro/mese, FV + accumulo, entro 3 mesi, telefono verificato). QUALIFIED → Vicenza → Rossi Impianti → DELIVERY -1 → GHL → portale → sopralluogo → SHOW → preventivo 11.500 → WON. Il sistema ricostruisce Advertising → Lead → Qualifica → Cliente → Appuntamento → Vendita.

## 59. Principio prodotto

Cinque domande a cui rispondere sempre: quanti lead devo ancora a ogni cliente; dove deve andare ogni nuovo lead; perché un lead è stato o non è stato conteggiato; quanto guadagno realmente su ogni cliente e campagna; cosa è successo al lead dopo la consegna.

## 60. Direzione futura

Modello dati non legato al fotovoltaico: climatizzazione, infissi, caldaie, immobiliare, assicurazioni, finanziamenti, servizi B2B. I campi specifici vivono in template e custom field, non nella struttura centrale.

---

## Stato di implementazione (prima release)

| Sezione | Stato | Note |
|---|---|---|
| 1–3 Visione, architettura, ruoli | fatto | RBAC su ogni route; Manager senza economics |
| 4 Dashboard admin | fatto | KPI e filtri periodo/cliente/provincia/regione/campagna/fonte/operatore/tipo |
| 5 Clienti | fatto | scheda completa, utenti portale, criteri per cliente |
| 6–7 Pacchetti e ledger | fatto | saldo = somma transazioni, lock in consegna, rettifica manuale solo Super Admin |
| 8–9 Lead e stati | fatto | macchina a stati con transizioni ammesse, storico con utente e motivo |
| 10–13 Routing, esclusività, cap, coda | fatto | esclusiva gerarchica, cap su fuso Europe/Rome, coda con motivi e retry |
| 14 Duplicati | fatto | telefono/email = duplicato, indirizzo+cognome = possibile; finestra configurabile |
| 15–16 Prequalifica e score | fatto | template JSON con salti, criteri, score; modificabili da Impostazioni |
| 17–18 GHL | fatto | uscita: contatto, opportunità, tag, custom field, nota; entrata: webhook idempotente |
| 19 Calendari con slot | fase 2 | appuntamenti registrati a mano o da webhook GHL |
| 20 Appuntamenti | fatto | stati e collegamenti; per l'offerta "lead + appuntamento" addebito al booking |
| 21 Reminder | fase 2 | delegati a GHL |
| 22–24 Replacement e SLA | fatto | portale cliente, decisione Manager/Admin, +1 nel ledger, override fuori SLA |
| 25–27 Portale, esito, analytics cliente | fatto | segregazione dal token; funnel e dati mancanti |
| 28–31 Analytics interne | parziale | dashboard, analytics per cliente, economics per campagna; costi commerciali/delivery non ancora attribuiti |
| 32–34 Notifiche, alert, rinnovo | fatto/parziale | in-app + Slack; email in fase 2; rinnovo = nuovo pacchetto pagato con retry coda |
| 35 Billing | fatto (MVP) | registrazione manuale pagamento; Stripe fase 2 |
| 36 Audit log | fatto | ogni azione di credito, stato, assegnazione, GHL |
| 37–40 Data model, API, webhook | fatto | 25 tabelle, API-first, eventi in uscita firmati |
| 41 Privacy | fatto/parziale | JWT, RBAC, tenant, anonimizzazione, consenso; retention automatica e backup a livello infrastruttura |
| 42–47 UX, ricerca, filtri, export | fatto | schermata chiamata a tre colonne; export CSV (XLSX fase 2) |
| 48 MVP | fatto | tutte le 20 funzioni elencate |
