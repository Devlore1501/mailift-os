# Lead on Demand: review settimanale delle call

> Copre due tipi di call: la **vendita agli installatori** (Lorenzo come
> closer, registrata su Fathom) e la **prequalifica telefonica ai lead finali**
> (script S4 della knowledge base, registrata in GHL). Per le discovery call
> Mailift eCommerce vedi [discovery_call_processing.md](discovery_call_processing.md).
>
> Fonte delle regole commerciali: `Lead_on_Demand_knowledge_base_AI.md` (v1.0,
> 1 ottobre 2026). In caso di dubbio su prezzi, esclusiva o promesse prevale
> quel documento, non questo.

## Decisioni di Lorenzo (1 ottobre 2026)

| Tema | Decisione |
|---|---|
| Scopo della review | Migliorare la vendita, giudicare la qualità dei prospect, controllare le promesse fatte |
| Perimetro | Vendita agli installatori più prequalifica ai lead finali |
| Follow-up automatico | Invio automatico solo per recap post call e messaggio a +1 giorno; il resto passa da Lorenzo |
| Canali | Email e SMS da GHL, più telefonata manuale. WhatsApp escluso per ora |
| Scritture su GHL | Anteprima e conferma di Lorenzo prima di ogni scrittura |
| Output | Notion: database con una riga per call più pagina di sintesi settimanale |
| Giorno | Venerdì pomeriggio |
| Target numerici | Baseline di 4 settimane, poi li fissa Lorenzo |
| Prequalifica, cosa valutare | Rispetto dello script, motivi di scarto, tasso di qualifica, promesse fatte al lead |
| Fonte audio prequalifica | Registrazioni delle chiamate GHL (accesso via API da verificare) |

## Obiettivo

1. Ogni venerdì sapere cosa è successo nelle call LOD della settimana, in numeri.
2. Per ogni call, registrare **perché** è stata chiusa o persa, da una lista fissa.
3. Scrivere esito, motivo e data di ricontatto nella scheda GHL del contatto.
4. Far partire da quei dati il follow-up e la riattivazione, senza dipendere dalla memoria.
5. Valutare anche il lavoro di prequalifica (sezione dedicata sotto).

## Definizione di "chiuso"

Firma e incasso sono due eventi distinti (KB sezioni 6 e 13). Una call è
**chiusa** solo a pagamento ricevuto. Gli stati intermedi vanno registrati
separatamente e non contano come vendita:

`call svolta → verifica necessaria → proposta inviata → attesa firma → firmato, attesa pagamento → pagato → attivo`

Più gli stati di uscita: `perso`, `rinviato a data concordata`, `non raggiunto`.
"Faccio il bonifico" detto in call non è un incasso: lo stato resta
"firmato, attesa pagamento" finché l'incasso non è verificato.

## Metriche settimanali

Definizioni dalla KB sezione 20. I target si fissano dopo 4 settimane di
baseline; non ci sono ancora dati osservati su cui calibrarli.

| Metrica | Calcolo |
|---|---|
| Call fissate / svolte | Show rate = svolte / fissate |
| Call con decisore presente | Svolte con decisore / svolte |
| Proposte inviate | Proposte / call svolte |
| Firme | Firmati / proposte inviate |
| Incassi | Pagati / firmati |
| Close rate | Pagati / call svolte |
| Tempo di recap | Ore tra fine call e recap inviato |
| Next step con data | Call con prossimo passo, responsabile e data / call svolte |
| Non chiusi con ricontatto pianificato | Non chiusi con data ricontatto / non chiusi |

Paletti già fissabili: recap il giorno stesso della call, next step con data
sul 100% delle call, ricontatto pianificato sul 100% dei non chiusi.

## Motivi di perdita (lista chiusa)

Un motivo primario, uno secondario opzionale, più una frase di contesto.

| Codice | Significato |
|---|---|
| `prezzo` | Costo per lead percepito alto rispetto a moduli o lead già comprati |
| `pagamento-anticipato` | Voleva pagare a vendita o a consumo |
| `fiducia-prova` | Chiede casi o numeri che oggi non sono documentabili |
| `zona-esclusiva` | Territorio o segmento non disponibile, o esclusiva non soddisfacente |
| `capacita` | Pochi commerciali o nessuno che richiami i contatti: cliente non adatto |
| `decisore` | Deve sentire un socio o un'altra persona |
| `timing` | Non adesso, con o senza data concordata |
| `esperienza-passata` | Ha già comprato lead scadenti e diffida |
| `garanzia-risultati` | Voleva una garanzia su appuntamenti o vendite che non diamo |
| `organico-pieno` | Ha già abbastanza richieste (caso Sunpark) |
| `silenzio-post-call` | Ha promesso di firmare o inviare documenti, poi è sparito |
| `fuori-target` | Segmento o profilo non servito |

Motivi di chiusura: `test-basso-rischio` (pacchetto da 10), `esclusiva`,
`prequalifica-telefonica`, `prezzo`, `fiducia-persona`, `urgenza-reale`,
`prova-documentata`.

## Scorecard della call

Voto da 1 a 5 su: qualità della discovery, gestione dell'obiezione principale,
next step fissato con data. Serve a separare lead sbagliato da call condotta male.

## Controllo promesse (KB sezioni 15, 20, 26)

Per ogni call, segnalare se compare uno di questi punti, con timestamp Fathom:

- garanzia di appuntamenti o vendite (il 50–70% è un claim, non una garanzia)
- pagamento a consumo o a fine mese
- sconto o bonus non autorizzato (il bonus da 5 lead non è riattivabile)
- "400+ contatti" o "20 partner attivi" usati come prova sociale (non verificati)
- zona dichiarata libera senza controllo
- servizio senza chiamata di prequalifica
- verifica SMS o consegna istantanea come funzioni già attive

## Review della prequalifica telefonica

Riferimento: script S4 (KB sezione 11) per le aziende, KB sezione 10 per il
residenziale. Per ogni chiamata registrata in GHL:

- **Rispetto dello script**: sequenza seguita (conferma richiesta, azienda e sede, spesa energia, proprietà, copertura, amianto, motivazione, decisori, disponibilità al confronto tecnico).
- **Esito e motivo di scarto**: qualificato, da verificare, non qualificato con motivo, non raggiunto. Mancata risposta e incompatibilità restano stati diversi.
- **Tasso di qualifica**: qualificati / lead chiamati, per coorte e campagna.
- **Promesse al lead**: risparmio garantito (l'80% non è ammesso), impianto gratuito, finanziamento approvato, incentivi, appuntamento già fissato, preventivo.
- **Applicazione delle regole**: soglia indicativa di 1.000 euro/mese per le aziende, amianto segnalato e non promesso, bolletta non inviata come non causa di scarto.

Prerequisito: verificare con il token GHL se l'API espone registrazioni e
trascrizioni delle chiamate. Se non le espone, si ripiega sui dati inseriti dal
qualificatore (esito, motivo, note) e il punto "promesse al lead" resta scoperto.

## Cadenza di follow-up

Proposta della KB sezione 14, non ancora decisione approvata. Una data
concordata col prospect prevale sempre sulla cadenza. Una risposta ferma la
sequenza automatica. Un "non chiamatemi più" la chiude.

| Quando | Azione | Condizione |
|---|---|---|
| Giorno della call | Recap e scheda offerta | Sempre |
| +1 giorno lavorativo | Messaggio breve | Nessuna data concordata |
| +3 | Telefonata, poi messaggio contestuale | Nessuna risposta |
| +5 | Risposta mirata all'obiezione o richiesta documentale motivata | Obiezione nota |
| +7 | Chiedere se proseguire o archiviare | Nessuna risposta |

Ramificazioni dal motivo registrato:

| Motivo | Azione |
|---|---|
| `timing` | Task alla data concordata, nessun sollecito prima |
| `decisore` | Concordare quando e chi coinvolgere |
| `prezzo` | Chiarire cosa include il pacchetto; solo test già autorizzati, nessuno sconto autonomo |
| `fiducia-prova` | Inviare materiale solo se verificato |
| `silenzio-post-call` | Verificare l'ostacolo (documenti, visura) senza presumere cattiva fede |
| `zona-esclusiva` | Citare la riserva solo se esiste ed è datata |
| `fuori-target`, rifiuto esplicito | Nessun follow-up, archivio |

Cosa parte da solo e cosa no, per decisione di Lorenzo:

| Messaggio | Invio | Canale |
|---|---|---|
| Recap post call, giorno della call | Automatico | Email GHL |
| Messaggio breve a +1 giorno lavorativo (solo senza data concordata e senza risposta) | Automatico | Email o SMS GHL |
| Telefonata a +3 giorni | Task per Lorenzo | Telefono |
| Risposta all'obiezione (+5), richiesta di proseguire o archiviare (+7) | Bozza e task per Lorenzo | Email o SMS dopo approvazione |
| Promemoria su data concordata, richiesta documenti, qualsiasi altro caso | Task per Lorenzo | A scelta di Lorenzo |

Il recap automatico deve rispettare il perimetro della KB: nessuna promessa
oltre quanto detto in call, prezzo e IVA espliciti, pagamento anticipato.

## Scheda GHL

Campi personalizzati da creare (nomi proposti):

`lod_esito`, `lod_stato_firma`, `lod_stato_pagamento`, `lod_motivo_primario`,
`lod_motivo_secondario`, `lod_obiezione`, `lod_pacchetto` (segmento, quantità,
prezzo, IVA), `lod_zona`, `lod_voto_call`, `lod_promesse_a_rischio`,
`lod_data_ricontatto`, `lod_tipo_ricontatto`, `lod_link_fathom`.

Tag: `lod-won-{codice}`, `lod-lost-{codice}`, `lod-cohort-{YYYY}-{MM}`.
Nota: riassunto fattuale, distinzione tra proposto e accettato, link Fathom.
Task: uno per ogni non chiuso, alla data di ricontatto.

Collegamento call → contatto (KB sezione 19): solo con identificativo verificato
o match univoco su email degli invitati o appuntamento GHL. La sola vicinanza
oraria non basta; i match ambigui vanno a Lorenzo. Il payload Fathom contiene la
sola email di Lorenzo, quindi l'email del prospect va letta dagli invitati del
calendario o dal contenuto della call.

## Esecuzione settimanale

Venerdì pomeriggio.

1. Elenco call di vendita da Fathom e chiamate di prequalifica da GHL.
2. Per ogni call: trascrizione, estrazione di esito, stato, motivo, obiezione, voti, promesse a rischio. Per la prequalifica, le voci della relativa sezione.
3. Abbinamento al contatto GHL; casi ambigui in coda per Lorenzo.
4. Anteprima delle scritture su GHL, una per call. Lorenzo conferma prima di ogni scrittura.
5. Scrittura di campi, nota, tag e task.
6. Notion: una riga nel database per ogni call, poi la pagina di sintesi della settimana con metriche, motivi di perdita per frequenza, due obiezioni ricorrenti, promesse a rischio, una azione da testare la settimana dopo.

Le prime 4 settimane servono da baseline: il report mostra i numeri senza
confronto con target. Poi Lorenzo li fissa.

## Livelli di automazione

1. **Manuale assistito** (ora): Claude esegue i passi 1–6 su richiesta, con anteprima e conferma.
2. **Routine schedulata**: script `tools/weekly_call_review.py` il venerdì che prepara le anteprime e la bozza Notion; la conferma delle scritture resta di Lorenzo.
3. **Workflow GHL**: tag del motivo come trigger di attesa, invio di recap e messaggio a +1 giorno, task per il resto della cadenza.

Un CRM esterno non è previsto: pipeline, workflow, CAPI e task sono già in GHL.

## Stato GHL verificato (1 ottobre 2026, sola lettura)

- Location: "Fotovoltaico On demand", fuso orario impostato su Europe/Amsterdam (non Europe/Rome: attenzione agli orari dei task e dei messaggi automatici).
- Pipeline `LOD Sales Process` (`TCEs0rbrDtxjBchAUPdx`), 5 stage: New Lead, Contacted, Fissata call, Proposal Sent, Closed. Mancano gli stati intermedi della KB (firmato, attesa pagamento, pagato, attivo): vanno tracciati con campi personalizzati, non con stage, a meno di modificare la pipeline.
- Opportunità: 40 in totale. Open: New Lead 3, Contacted 11, Fissata call 10, Proposal Sent 2. Lost: Contacted 6, Fissata call 2, Proposal Sent 4 (12 in tutto). Won: 2 in Closed. Per le 12 perse il motivo non è registrato in nessun campo, quindi il recupero storico dipende dalle trascrizioni.
- Campi personalizzati già presenti (6): fatturato annuo, Cliente Installatore, segmento su cui lavorano, persone che si occupano di vendita/preventivi, Ruolo in azienda, Proprietario Lead. Nessun campo per esito, motivo, obiezione o data di ricontatto.
- Tag già presenti: solo 7, nessuno con la convenzione `lod-won-*` / `lod-lost-*`.
- Registrazioni e trascrizioni delle chiamate: gli endpoint rispondono sulle chiamate di tipo `TYPE_CALL`. Il contenuto e la qualità delle trascrizioni vanno ancora controllati su un campione.

## Prerequisiti aperti

- Creazione dei campi personalizzati in GHL (a mano o via API, con scope dedicato).
- `tools/ghl_client.py` non scrive ancora i campi personalizzati: serve una funzione
  `set_custom_fields` che usi gli ID dei campi una volta creati.
- Conferma che tutte le call di vendita LOD siano registrate su Fathom.
- Controllo su un campione della qualità delle trascrizioni GHL delle chiamate di prequalifica.
- Decisione sul fuso orario della location (Amsterdam contro Roma).
- Struttura del database Notion (proprietà e nome) e pagina padre dove crearlo.
- Testi del recap e del messaggio a +1 giorno, da approvare prima dell'automazione.
- Approvazione della cadenza di follow-up e della lista motivi.
