# Decisioni tecniche

Registro delle scelte prese durante l'implementazione dell'MVP, con il motivo e il trade-off.

## Drizzle al posto di Prisma

Il PRD suggerisce Prisma. Drizzle produce SQL leggibile, non richiede un motore binario e supporta lo stesso schema sia con il driver `pg` sia con pglite (Postgres compilato in WebAssembly). Questo permette test end-to-end reali in memoria e un ambiente demo senza server. Trade-off: meno strumenti grafici e una curva di apprendimento leggermente diversa per chi conosce solo Prisma.

## Coda job su tabella Postgres invece di Redis + BullMQ

L'MVP ha poche decine di job al giorno (invio GHL, webhook, notifiche). Una tabella `jobs` con lock ottimistico `PENDING -> RUNNING`, tentativi, backoff esponenziale e stato `DEAD` copre il requisito di retry e alert (PRD sez. 55) senza un secondo servizio da gestire. Quando il volume crescerà, l'interfaccia `enqueue` e gli handler in `services/worker.ts` si spostano su BullMQ senza toccare i servizi.

## Consegna e addebito in un'unica transazione

`deliverLeadTx` fa lock sulla riga del pacchetto (`SELECT ... FOR UPDATE`), calcola il saldo come somma del ledger, rifiuta se il saldo non copre la consegna, inserisce `DELIVERY -1`, aggiorna lo stato del pacchetto e accoda il job GHL. Due operatori che consegnano l'ultimo credito nello stesso istante non possono entrambi riuscire.

## Il credito non dipende dal successo dell'invio a GHL

Il lead è contrattualmente consegnato quando viene assegnato e addebitato; l'invio a GHL è un effetto asincrono. Se GHL è irraggiungibile dopo cinque tentativi, il lead passa a `DELIVERY_FAILED`, l'admin riceve una notifica critica e può reinviare dalla scheda lead. Il credito resta addebitato e il lead resta visibile nel portale, perché il cliente lo ha comunque ricevuto.

## Il saldo è sempre una somma

Nessuna colonna `lead_residui`. Tutte le letture del saldo sommano `package_transactions`. Le rettifiche manuali sono transazioni `MANUAL_ADJUSTMENT` con motivazione obbligatoria, riservate al Super Admin, e finiscono nell'audit log.

## Template di qualifica come dati

Domande, salti condizionali, criteri e regole di score vivono in `qualification_templates` (JSON) e sono modificabili dal pannello Impostazioni. I criteri specifici del cliente stanno sulla scheda cliente e vengono valutati dal Routing Engine sulle risposte del lead. Il fotovoltaico è solo il seed iniziale: un nuovo verticale è un nuovo template più i territori e i clienti.

## Cap calcolati sul fuso Europe/Rome

Giorno, settimana e mese per i cap di consegna si calcolano sul fuso italiano, indipendentemente dal fuso del server. Una consegna alle 00:30 italiane conta nel giorno giusto anche se il server è in UTC.

## Portale cliente segregato dal token

Le route `/portal/*` ricavano il `clientId` dal JWT dell'utente e filtrano ogni query su quel valore. Il frontend non passa mai l'id cliente. Un utente cliente che prova a chiamare le route staff riceve 403; un lead di un altro cliente risponde 404.

## Codici leggibili

Lead `LD-000123`, clienti `CLI-0004`, pacchetti `PV-2026-00031` tramite tabella `counters` con upsert atomico. Gli UUID restano le chiavi primarie; i codici servono a persone e a GHL (tag `lod:ld-000123`).

## Cosa resta fuori dall'MVP

Calendari esterni con slot disponibili, reminder, Stripe, round robin configurabile, multi-verticale con più organizzazioni, email transazionali. Le tabelle e gli eventi sono già predisposti (appuntamenti con `calendar_provider`/`external_id`, eventi in uscita, stati pacchetto `AWAITING_PAYMENT`), ma l'implementazione è rimandata alla fase 2 del PRD.
