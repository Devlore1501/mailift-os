# Questionario di onboarding su GHL, cliente lead gen B2B

Sostituisce la call di setup. Deriva da `clients/mida-energy/onboarding-form-lead-gen-ppl.md`. Il cliente compila in 10–12 minuti da telefono; la call resta solo se scatta una delle condizioni della sezione "Quando serve ancora una call".

Come costruirlo in GHL: Sites > Forms > Builder > nuovo form multi-step (un passo per sezione, barra di avanzamento attiva). Prima di creare il form, creare i custom field del contatto con le chiavi della colonna "Chiave" (Settings > Custom Fields, cartella "Onboarding lead gen"). Il nome cliente nell'URL arriva dal link con parametri, vedi sezione "Invio".

Legenda tipi: T testo breve, TL testo lungo, N numero, R radio, C checkbox multiplo, D menu a tendina, F upload file, Tel telefono, E email. Obbl. = obbligatorio.

---

## Testo introduttivo (campo Rich Text in alto)

Ciao {{contact.first_name}}, questo questionario ci serve per scrivere gli annunci e lo script di qualifica con le vostre regole, senza farvi perdere tempo in una call. Servono circa 10 minuti. Rispondete come rispondereste a un vostro commerciale nuovo: più siete precisi su cosa NON volete, meno lead sprecati riceverete. Le risposte si salvano a ogni passo, potete riprendere dopo.

---

## Passo 1, Referenti

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Ragione sociale | T | Sì | ob_ragione_sociale |
| Chi segue la parte commerciale (nome e cognome) | T | Sì | ob_ref_commerciale |
| Telefono del referente commerciale | Tel | Sì | ob_tel_commerciale |
| Chi segue la parte amministrativa (nome, email) | T | Sì | ob_ref_amministrativo |
| Chi deve ricevere l'avviso di ogni nuovo lead (email, anche più di una separate da virgola) | T | Sì | ob_email_alert |
| Volete l'avviso anche su WhatsApp? Se sì, numero | T | No | ob_whatsapp_alert |
| Chi decide in caso di dubbio sul messaggio degli annunci | T | Sì | ob_decisore_messaggio |

## Passo 2, Offerta

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Con quale formula chiudete di solito? | C: Noleggio operativo / Acquisto diretto / Finanziamento / Bandi e incentivi / Altro | Sì | ob_formula |
| Se "Altro": quale | T | Condizionale | ob_formula_altro |
| Spiegate la formula principale in una frase, come la direste a un cliente | TL | Sì | ob_formula_frase |
| Qual è il numero concreto che usate in trattativa (canone, coefficiente, risparmio tipo, durata)? | TL | Sì | ob_numero_trattativa |
| Quali promesse o incentivi NON volete vedere negli annunci? | TL | Sì | ob_no_promesse |
| Un lead che preferisce un'altra formula, lo volete comunque? | R: Sì / No / Solo se... | Sì | ob_lead_altra_formula |
| Se "Solo se...": a quali condizioni | T | Condizionale | ob_lead_altra_formula_cond |

Logica: mostrare i campi con "Condizionale" solo se la risposta precedente è "Altro" o "Solo se...".

## Passo 3, Differenziatori e prove

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Siete installatori/produttori diretti o intermediari? | R: Diretti / Intermediari / Entrambi | Sì | ob_diretti |
| Numeri verificabili che aumentano la fiducia (anni di attività, impianti realizzati, squadre, certificazioni) | TL | Sì | ob_numeri_fiducia |
| Link a recensioni, casi o pagine con foto di lavori realizzati | TL | No | ob_link_prove |
| Caricate 5–10 foto di lavori reali (no foto stock) | F, max 10 | No | ob_foto_lavori |
| Logo in alta risoluzione | F | No | ob_logo |
| Cosa hanno promesso e non mantenuto le agenzie o i concorrenti con cui avete lavorato | TL | No | ob_esperienze_negative |

## Passo 4, Target (blocca il lancio)

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Chi è il vostro cliente ideale (tipo di azienda, settore) | TL | Sì | ob_target_ideale |
| Soglia minima di consumo o spesa per considerarlo idoneo (es. bolletta mensile in euro) | T | Sì | ob_soglia_minima |
| Regioni o province prioritarie | TL | Sì | ob_zone_priorita |
| Zone limitrofe accettabili, e fino a dove | TL | No | ob_zone_limitrofe |
| Zone da escludere | T | No | ob_zone_escluse |
| Chi NON volete (privati, condomini, aziende sotto soglia, settori) | TL | Sì | ob_target_escluso |
| Chi decide di solito in azienda | C: Amministratore / Titolare / Energy manager / Responsabile acquisti / Varia | Sì | ob_decisore_tipo |
| Quanti appuntamenti nella stessa zona servono perché valga la trasferta | N | Sì | ob_min_appuntamenti_zona |

## Passo 5, Qualifica

Per ogni criterio chiedere: obbligatorio, desiderabile, eliminatorio. Nel form è una tabella di radio (riga = criterio, colonna = valore).

| Criterio (riga) | Valori (colonne) | Chiave |
|---|---|---|
| Soglia di spesa/consumo | Obbligatorio / Desiderabile / Eliminatorio / Non rilevante | ob_q_soglia |
| Condizione fisica del sito (es. tetto) | idem | ob_q_sito |
| Elemento che esclude il lead (es. amianto) | idem | ob_q_esclusione |
| Solvibilità | idem | ob_q_solvibilita |
| Decisore presente o coinvolto | idem | ob_q_decisore |
| Copia di un documento (es. bolletta) | idem | ob_q_documento |
| Disponibilità dichiarata all'appuntamento | idem | ob_q_appuntamento |

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Altri criteri che per voi sono eliminatori | TL | No | ob_q_altri |
| Chi verifica la solvibilità | R: Voi / Noi / Entrambi | Sì | ob_chi_solvibilita |
| Quali lead non volete ricevere mai (es. chi chiede solo il prezzo al telefono) | TL | Sì | ob_lead_vietati |
| Descrivete un lead perfetto che avete avuto (azienda, richiesta, perché è andato bene) | TL | Sì | ob_esempio_lead_buono |
| Descrivete un lead che vi ha fatto perdere tempo | TL | Sì | ob_esempio_lead_cattivo |

## Passo 6, Obiezioni e freni

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Le 3–5 obiezioni che sentite più spesso | TL | Sì | ob_obiezioni |
| Perché chi non ha ancora comprato non l'ha fatto | TL | Sì | ob_perche_non_comprano |
| Cosa spinge all'acquisto | TL | Sì | ob_motivazioni_acquisto |
| L'argomento con cui chiudete più spesso | TL | No | ob_argomento_chiusura |

## Passo 7, Consegna dei lead (blocca il lancio)

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Dove volete ricevere i lead | R: Foglio Excel/Google Sheets condiviso / CRM / Solo email / Altro | Sì | ob_formato_consegna |
| Se CRM o Altro: nome e come integrarlo | T | Condizionale | ob_formato_dettaglio |
| Email Google a cui dare accesso al foglio | E | Condizionale (se foglio) | ob_email_foglio |
| Campi extra oltre a nome, azienda, telefono, email, risposte di qualifica | TL | No | ob_campi_extra |
| Entro quante ore ricontattate un lead consegnato | R: Entro 1 ora / Entro 4 ore / Entro 24 ore / Non c'è una regola | Sì | ob_sla_ricontatto |
| Chi fissa l'appuntamento | R: Il vostro commerciale / Noi per conto vostro | Sì | ob_chi_fissa |
| Come vi avvisiamo se un lead non è valido, e come lo contestate | TL | No | ob_contestazioni |

## Passo 8, Volumi e amministrativo

| Domanda | Tipo | Obbl. | Chiave |
|---|---|---|---|
| Quanti lead qualificati al mese potete gestire senza perderli | N | Sì | ob_volume_max |
| Quanti ne vorreste nel primo mese | N | Sì | ob_volume_target |
| Data in cui potete iniziare a ricevere lead | Data | Sì | ob_data_inizio |
| Intestazione per fattura (ragione sociale, P.IVA, SDI/PEC) | TL | Sì | ob_dati_fattura |
| Avete già pagato? (bonifico) | R: Sì / No / In corso | Sì | ob_pagato |
| Allegate la contabile se avete pagato | F | Condizionale | ob_contabile |
| Altro che dovremmo sapere | TL | No | ob_note_finali |

## Conferma finale

Checkbox obbligatoria: "Confermo che i criteri indicati sono quelli con cui valuterete i lead che riceverete". Serve a evitare contestazioni successive sulla qualità.

---

## Invio del questionario

Link con parametri: `https://<dominio-form>/onboarding?first_name=...&company=...`; in alternativa invio da un workflow con il link del form e il merge field del contatto. Tenere un solo link per cliente, con il contatto già esistente in GHL, così le risposte finiscono sul contatto giusto.

## Workflow GHL (Automation > Workflows)

Nome: `Onboarding lead gen, questionario`

Trigger A, invio: tag `cliente-leadgen-nuovo` aggiunto. Azioni, in ordine:
1. Invia email (e WhatsApp se attivo) con il link al questionario e il tempo stimato.
2. Imposta tag `onboarding-inviato`.
3. Attendi 1 giorno. Condizione: tag `onboarding-compilato` assente. Se assente, invia promemoria 1.
4. Attendi 2 giorni. Stessa condizione, promemoria 2 con testo "bloccati: senza questo non possiamo far partire le campagne".
5. Attendi 2 giorni. Stessa condizione: crea task interno "Chiamare il cliente per completare onboarding" e notifica interna.

Trigger B, form inviato (Form Submitted = questionario onboarding). Azioni:
1. Aggiungi tag `onboarding-compilato`, rimuovi `onboarding-inviato`.
2. Sposta l'opportunità nella pipeline "Clienti lead gen" allo stage "Onboarding ricevuto".
3. Condizione "Controllo completezza", rami:
   - Se `ob_soglia_minima`, `ob_zone_priorita`, `ob_target_escluso`, `ob_formato_consegna` e `ob_email_alert` sono tutti valorizzati: tag `onboarding-completo`, notifica interna "pronto per brief annunci".
   - Altrimenti: tag `onboarding-incompleto`, task "Chiedere via WhatsApp i dati mancanti".
4. Condizione "Serve call" (vedi regole sotto): se una regola scatta, invia al cliente il link di prenotazione del calendario "Call 15 minuti" e tag `serve-call`.
5. Email interna a Lorenzo con riepilogo di tutte le risposte (merge fields dei custom field).
6. Email di conferma al cliente: "Abbiamo ricevuto tutto. Prossimo passo: [data lancio]. Vi scriviamo quando le campagne sono pronte per la vostra revisione."

Importante: nei Condition di GHL non mettere azioni importanti nel ramo "none of the above", come già indicato in `workflows/discovery_call_processing.md`.

## Quando serve ancora una call

La call da 15 minuti si propone solo se:
- ob_formula = "Altro" o ob_lead_altra_formula = "Solo se...".
- ob_zone_priorita lasciato generico (es. "tutta Italia") con ob_soglia_minima vuota o sotto 500 euro.
- ob_esempio_lead_buono e ob_esempio_lead_cattivo hanno meno di 20 caratteri ciascuno.
- ob_formato_consegna = "CRM" o "Altro".
- ob_pagato = "No" oltre 48 ore dall'invio del questionario.

Le prime quattro si implementano con condizioni sui campi (contiene, è vuoto, lunghezza); l'ultima con un'attesa e un controllo sul tag di pagamento.

## Cosa fa Mailift dopo l'invio

1. Entro 24 ore: aprire il contatto, leggere le risposte, scrivere in `clients/<cliente>/onboarding.md` la versione pulita (stesso schema di `clients/mida-energy/onboarding-form-lead-gen-ppl.md`).
2. Derivare tre cose dalle risposte: angoli di annuncio (passi 2, 3, 6), script di qualifica telefonica (passo 5), struttura del foglio di consegna e testo dell'alert (passo 7).
3. Mandare al cliente, per approvazione scritta, testo e criteri di qualifica prima di lanciare. È l'ultima occasione per bloccare una promessa che il commerciale non onorerebbe.

## Differenze rispetto alla call

La call ha permesso a Rosario di raccontare a voce le obiezioni e i motivi per cui i clienti non comprano; per iscritto questo contenuto tende a essere più breve. Per questo il passo 6 ha domande aperte obbligatorie e il passo 5 chiede due esempi concreti di lead (buono e cattivo). Se dopo i primi due questionari le risposte del passo 6 risultano troppo scarne, aggiungere un campo audio (GHL non lo ha nativo: usare un link Loom o un messaggio vocale WhatsApp richiesto nel workflow di promemoria).
