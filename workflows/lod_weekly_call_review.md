# Lead on Demand: review settimanale delle call

> Copre le call di vendita agli **installatori** (Lorenzo come closer). Le
> telefonate di prequalifica ai lead finali (script S4 della knowledge base) sono
> un altro flusso e restano fuori da questa review. Per le discovery call Mailift
> eCommerce vedi [discovery_call_processing.md](discovery_call_processing.md).
>
> Fonte delle regole commerciali: `Lead_on_Demand_knowledge_base_AI.md` (v1.0,
> 1 ottobre 2026). In caso di dubbio su prezzi, esclusiva o promesse prevale
> quel documento, non questo.

## Obiettivo

1. Ogni venerdì sapere cosa è successo nelle call LOD della settimana, in numeri.
2. Per ogni call, registrare **perché** è stata chiusa o persa, da una lista fissa.
3. Scrivere esito, motivo e data di ricontatto nella scheda GHL del contatto.
4. Far partire da quei dati il follow-up e la riattivazione, senza dipendere dalla memoria.

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

1. Elenco call LOD della settimana da Fathom.
2. Per ogni call: trascrizione, estrazione di esito, stato, motivo, obiezione, voti, promesse a rischio.
3. Abbinamento al contatto GHL; casi ambigui in coda per Lorenzo.
4. Anteprima delle scritture su GHL. Nessuna scrittura senza conferma finché il metodo non è validato.
5. Scrittura di campi, nota, tag e task.
6. Report di una pagina: metriche, motivi di perdita per frequenza, due obiezioni ricorrenti, promesse a rischio, un'azione da testare la settimana dopo.

## Livelli di automazione

1. **Manuale assistito** (ora): Claude esegue i passi 1–6 su richiesta, con conferma.
2. **Routine schedulata**: script `tools/weekly_call_review.py` il venerdì, con correzione umana dei soli casi dubbi.
3. **Workflow GHL**: tag del motivo come trigger di attesa, task e messaggi della cadenza.

Un CRM esterno non è previsto: pipeline, workflow, CAPI e task sono già in GHL.

## Prerequisiti aperti

- Nome della pipeline GHL LOD e dei suoi stage.
- Creazione dei campi personalizzati in GHL (a mano o via API, con scope dedicato).
- `tools/ghl_client.py` non scrive ancora i campi personalizzati: serve una funzione
  `set_custom_fields` che usi gli ID dei campi una volta creati.
- Conferma che tutte le call LOD siano registrate su Fathom.
- Approvazione della cadenza di follow-up e della lista motivi.
