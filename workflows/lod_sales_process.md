# Lead on Demand: processo di vendita agli installatori

Fonte principale dei lead: **Facebook (paid social)**. Stato al 1 ottobre 2026.

Legenda dei marcatori:

- `[OSS]` osservato nei dati reali di GHL (messaggi inviati, log, pipeline, calendari).
- `[VER]` esiste ma l'API non espone i passaggi interni: da verificare aprendo il flusso.
- `[PROP]` proposta nuova, non ancora attiva. Le cadenze vengono dalla knowledge base (sezione 14) e dalle decisioni prese il 1 ottobre.

## 1. Cosa c'è oggi in GHL

Location "Fotovoltaico On demand", pipeline `LOD Sales Process`, 40 opportunità: 38 su 40 hanno come fonte Facebook (attribuzione "facebook / Paid Social"), 1 inserita a mano nel CRM, 1 senza fonte.

| Flusso GHL | Stato | Cosa fa (dedotto dai messaggi reali) |
|---|---|---|
| New Lead faceook | pubblicato | Alla compilazione del modulo crea l'opportunità in New Lead e manda l'SMS "richiesta ricevuta" (visto circa 22 volte) |
| Gestione telefono | pubblicato | Registrazione delle chiamate, note con riassunto AI, SMS dopo chiamata persa `[VER]` |
| Pre-Call Email Reminders | pubblicato | Conferma appuntamento, promemoria a 24 ore e a 1 ora, SMS con il link Meet |
| contratto | pubblicato | Invia il documento da firmare, via SMS e email |
| fathom | pubblicato | Incolla in nota il riassunto Fathom con il link alla registrazione |
| recap call | pubblicato | Recap dopo la call `[VER]` contenuto |
| POST CALL | bozza | Non attivo: il post-call è oggi manuale |
| Follow-Up Presentazione Non Convertita | bozza | Non attivo: il follow-up dopo la proposta è oggi manuale |

Moduli: "qualifica" (il modulo Facebook/landing con fatturato, segmento, persone di vendita, ruolo), "Form Fiscale", "Survey 0". Calendari: "Consulenza Conoscitiva" (30 minuti) e "Proposta e collaborazione" (30 minuti).

Due osservazioni che pesano sul processo:

1. I due flussi che dovrebbero coprire il follow-up (POST CALL e Follow-Up Presentazione Non Convertita) sono in bozza. È il punto in cui oggi ti dimentichi i contatti.
2. Tra gli 8 flussi non ce n'è nessuno per i segnali di qualità a Meta (CAPI). Con Facebook come fonte principale, gli stage non rimandano a Meta chi ha fissato una call o ha firmato `[VER]`.

## 2. Mappa generale

```
 META ADS (Facebook, paid social)                              38 contatti su 40 [OSS]
        |
        v
 +-------------------------------------------+
 | MODULO "qualifica"                        |  fatturato, segmento, persone di vendita,
 | (lead form Facebook o landing)  [VER]     |  ruolo in azienda [OSS]
 +-------------------------------------------+
        |  crea contatto + opportunita  [OSS]
        v
 +-------------+   +-------------+   +--------------+   +--------------+   +----------+
 | 1 NEW LEAD  |-->| 2 CONTACTED |-->| 3 FISSATA    |-->| 4 PROPOSAL   |-->| 5 CLOSED |
 |             |   | prequalifica|   |    CALL      |   |    SENT      |   | firmato  |
 +-------------+   +-------------+   +--------------+   +--------------+   +----------+
   SMS auto          chiamate +        conferma +         scheda +            pagamento
   [OSS]             script 8 passi    promemoria         contratto           onboarding
                                       [OSS]              [OSS]               avvio
        |                 |                 |                  |                  |
        +-----------------+-----------------+------------------+                  |
                          |                                                       v
                          v                                                  RIACQUISTO
              +-----------------------+                                      (pacchetto
              | PERSO  o  RINVIATO    |                                       successivo)
              | motivo + data ricontatto
              +-----------------------+
```

Tutto ciò che sta "in mezzo" a ogni stage (tentativi, esiti, rami) è gestito con i campi `LOD` (esito, stato firma, stato pagamento, motivo, data ricontatto). Gli stage restano 5.

## 3. Blocco 1: ingresso del lead (New Lead)

```
 [Lead compila il modulo su Facebook]
        |
        v
 crea contatto + opportunita in NEW LEAD                    [OSS]
        |
        v
 SMS automatico "abbiamo ricevuto la sua richiesta...       [OSS]
 ti contatteremo a breve, risponda per le preferenze
 di orario"
        |
        v
 SE il lead risponde con un orario  --->  CALL a quell'orario (vai al Blocco 2)
 SE non risponde                    --->  CALL entro [tempo da definire]  [PROP]
        |
        v
 primo tentativo fatto  --->  sposta a CONTACTED
```

Nota osservata: il primo SMS parte subito, ma la prima chiamata arriva spesso dopo uno o due giorni (esempio: modulo il 26/09 alle 22:02, prima chiamata il 28/09 alle 10:49). Il tempo di prima chiamata è una metrica da misurare.

## 4. Blocco 2: primo contatto e prequalifica (Contacted)

### 2a. Tentativi di contatto

```
 TENTATIVO 1 (chiamata)
     |
     +-- risponde ------------------------------> vai a 2b (script)
     |
     +-- non risponde
           |
           v
     SMS "ho provato a chiamarti... mi lascia un paio di orari"      [OSS]
           |
           v
 TENTATIVO 2 (altro orario, giorno dopo)       [PROP]
     +-- risponde ------------------------------> vai a 2b
     +-- non risponde ---> SMS/WhatsApp personale con riferimento alla richiesta
           |
           v
 TENTATIVO 3 (terzo giorno lavorativo)         [PROP]
     +-- risponde ------------------------------> vai a 2b
     +-- non risponde
           |
           v
 MESSAGGIO DI CHIUSURA (giorno 5)               [PROP]
 "hai richiesto informazioni, lavoriamo in esclusiva di zona,
  la disponibilita va verificata; se e ancora attuale scrivimi,
  altrimenti archivio la richiesta"
           |
           +-- risponde ---------------------------> vai a 2b
           +-- nessuna risposta dopo 3 giorni lavorativi
                   |
                   v
           esito NON-RAGGIUNTO  ---> opportunita PERSA, motivo non-determinabile
           ricontatto di riattivazione dopo 60 giorni  [PROP]
```

Se il lead ti chiede di richiamarlo a una certa ora, si crea un task con quell'ora esatta e si richiama a quell'ora (esempi nelle note: "richiamare 17 in poi", "chiamare 11,30"). Se l'ora passa senza richiamo, il messaggio di scuse è il primo punto del giorno dopo.

### 2b. Script di prequalifica (8 passi)

```
 1 APERTURA   "hai quattro minuti?"
      |
      +-- non puo parlare ---> concordare ORARIO PRECISO ---> task di richiamo
      |
      v
 2 MOTIVO     perche cerca questo servizio ora; come acquisisce oggi;
      |       se ha gia comprato lead: com'e andata
      v
 3 CAPACITA   persone di vendita (confronta col modulo), chi richiama,
      |       quanto in fretta, quanti lavori al mese gestibili
      |       +-- modulo e chiamata non coincidono ---> correggi il campo in GHL
      v
 4 COSA RICEVE   prequalifica = interesse + disponibilita a essere richiamati
      |          (NON un appuntamento prenotato); campagne a nostro carico
      v
 5 FASCIA DI PREZZO   residenziale 100-130 euro, aziende 150-200 euro e oltre
      |              (si dice la fascia, non si presenta l'offerta)
      |
      +-- fascia FUORI budget ----------> chiudi: PERSO, motivo prezzo
      |                                    (se lascia una porta aperta, es. B2B:
      |                                     rinviato con data, non perso)
      v
 6 DECISORE   "decidi da solo o con un socio?"        ---> vedi ramo sotto
      |
      v
 7 APPUNTAMENTO   solo se interessato: 2 opzioni di giorno e ora, 25-35 minuti
      |
      v
 8 CONFERMA   giorno, ora, partecipanti, email dell'invito; chiede di tenere
              pronti i dati sulle richieste gia gestite
              ---> sposta a FISSATA CALL
```

### 2c. Ramo decisore (vale in prequalifica e in discovery)

```
 "Decidi da solo o con un socio?"
        |
        +--------------------- E' IL DECISORE --------------------+
        |   (titolare, amministratore, "decido io")               |
        |                                                         v
        |                                              prosegui al passo 7: slot
        |
        +--------------------- NON E' IL DECISORE ----------------+
            ("devo sentire i soci", "decide un altro")            |
                    |                                             |
                    v                                             |
           "Chi partecipa alla decisione?"                        |
                    |                                             |
        +-----------+-------------------------+                   |
        |                                     |                   |
   si puo coinvolgere                   non si puo coinvolgere    |
   subito                               adesso                    |
        |                                     |                   |
        v                                     v                   |
 slot con ENTRAMBI                    NON si presenta proposta    |
 ("cerchiamo un orario                esito RINVIATO, motivo      |
  in cui possiate esserci             decisore                    |
  entrambi")                          task con DATA su cui        |
        |                             il decisore si e impegnato  |
        v                             nessun sollecito prima      |
 FISSATA CALL con il decisore         di quella data              |
                                      se non c'e una data: un solo|
                                      messaggio di chiusura       |
                                      dopo 5 giorni  [PROP]       |
```

Casi reali di fine settembre: Ignazio ("non decido io": decisore mai coinvolto, poi no-show), Grandi (socio, call con il socio dopo una settimana), Altamura (deve parlarne internamente, a distanza di due settimane non l'aveva ancora fatto), Carbone (soci, poi silenzio). Il ramo "non coinvolgibile adesso" è il punto debole: i quattro casi si sono fermati lì. Il segnale del modulo "Ruolo in azienda" (titolare / amministratore / direttore commerciale / altro) permette di sapere prima se probabilmente parli con il decisore `[PROP]`.

## 5. Blocco 3: appuntamento fissato (Fissata call)

```
 PRENOTAZIONE sul calendario "Consulenza Conoscitiva"
        |
        v
 SMS + EMAIL di conferma con link Meet                              [OSS]
        |
   24 ore prima:  EMAIL promemoria                                   [OSS]
                  SMS promemoria (variante: "rispondi per
                  confermare, altrimenti verra cancellato")          [OSS]
        |
   giorno della call, mattina:  SMS manuale "mi confermi che ci sarai?"   [OSS manuale]
        |
   1 ora prima:  EMAIL + SMS con link Meet                           [OSS]
        |
        v
 ORARIO DELLA CALL
        |
        +-- il lead si collega -------------------------> CALL (Blocco 4)
        |
        +-- chiede di spostare ---> nuovo slot (max 1 volta) ---> nuovo ciclo promemoria
        |
        +-- NON si presenta (NO-SHOW)
              |
              v
        dopo 10 minuti: SMS "ti sto aspettando in chiamata"          [OSS manuale]
              |
              v
        stesso giorno: UN messaggio di recupero [PROP]
        "mi hai fatto aspettare in call; lavoriamo in esclusiva di zona,
         la disponibilita va verificata; scegli tu un nuovo orario
         (2 opzioni) o archivio la richiesta"
              |
              +-- risponde con orario ---------> nuova FISSATA CALL
              +-- nessuna risposta fino al lunedi dopo
                      |
                      v
                esito NO-SHOW chiuso ---> opportunita PERSA, motivo silenzio-post-call
```

Nota: il promemoria con "rispondi per confermare, altrimenti verrà cancellato" può cancellare l'appuntamento senza che nessuno se ne accorga (caso Ignazio del 30/09). Verificare in GHL se l'appuntamento viene davvero annullato e, in quel caso, togliere la frase o aggiungere un avviso a te.

## 6. Blocco 4: call di discovery e vendita

```
 CALL (Meet, registrata da Fathom)
        |
        +-- Fathom registra, il flusso "fathom" incolla riassunto + link in nota  [OSS]
        |
        v
 STRUTTURA DELLA CALL (Sandler, dai riassunti Fathom)
   rapporto -> contratto iniziale (agenda, tempo, esito atteso) -> problema ->
   chi decide -> budget/fascia -> soluzione -> prossimo passo CON DATA
        |
        v
 DECISORE PRESENTE?
        |
        +-- NO ---> non presentare la proposta; dare solo processo e fascia;
        |           prenotare "Proposta e collaborazione" con il decisore;
        |           esito RINVIATO, motivo decisore, task con data            [PROP]
        |
        +-- SI ---> FIT? (segmento servito, capacita di richiamare, zona libera)
                       |
                       +-- NO ---> PERSO, motivo fuori-target / capacita
                       |
                       +-- SI ---> presenta pacchetto (test da 10 contatti)
                                      |
                                      +-- "procediamo" -> scheda + contratto
                                      |                   (Blocco 5)
                                      +-- obiezione ---> ramo obiezioni (sotto)
                                      +-- "ci penso"  -> prossimo passo con DATA
                                                         (vedi regola next step)
```

Regola del prossimo passo `[PROP]`: ogni call chiude con azione, responsabile e data o ora. Nelle 13 call di vendita analizzate, solo 5 hanno chiuso con una data.

```
 RAMO OBIEZIONI (codici motivo)
   prezzo                -> chiarire cosa e incluso (campagne + prequalifica),
                            il test e il modo per verificare; nessuno sconto
                            anticipato per iscritto
   pagamento-anticipato  -> standard prepagato; alternativa solo test da 10
   fiducia-prova         -> non inventare referenze; il test e la prova
   zona-esclusiva        -> disponibilita da verificare; esclusiva per segmento
                            e durata del pacchetto, con pattuizione scritta
   capacita              -> chi richiama i contatti e quanto in fretta;
                            pacchetto adeguato alla capacita
   decisore              -> ramo decisore (2c)
   timing                -> data concordata dal lead, nessun sollecito prima
   esperienza-passata    -> chiedere cosa non ha funzionato e confrontarlo
                            con i controlli prima della consegna
```

## 7. Blocco 5: proposta inviata

```
 "PROCEDIAMO"
        |
        v
 raccogliere DATI FISCALI (modulo "Form Fiscale" o messaggio)
        |
        v
 sposta a PROPOSAL SENT                                              [PROP] se non automatico
 invia SCHEDA + CONTRATTO dal flusso "contratto":
   SMS "You've received a new document... Sign it here"   (in inglese!)  [OSS]
   EMAIL "DOCUMENTO PER <nome>"                                          [OSS]
 stato firma = proposta, pagamento = nessuno
        |
        v
 CADENZA DI FOLLOW-UP (giorni lavorativi, si ferma alla risposta)    [PROP, KB sez. 14]
   G0   recap + scheda
   G+1  messaggio breve (solo se non c'e una data concordata)
   G+3  telefonata; se assente, messaggio contestuale
   G+5  risposta mirata all'obiezione o richiesta documentale motivata
   G+7  "proseguiamo o archivio?" con scadenza
        |
        v
 RISPOSTA DEL LEAD
   |
   +-- "firmo" ------------------> firmato, in attesa di pagamento (Blocco 6)
   |
   +-- "devo sentire il socio" --> data concordata, nessun sollecito prima;
   |                               proporre una call con tutti
   |
   +-- "prezzo / pagamento" -----> ramo obiezioni (Blocco 4), poi G+5
   |
   +-- "mi manca un documento" --> spiegare la finalita, concordare una data
   |
   +-- silenzio -----------------> G+7 con scadenza chiara; poi
                                   PERSO, motivo silenzio-post-call
                                   (esempio: Tiziano, 13 contatti dopo il contratto)
```

I due flussi `Follow-Up Presentazione Non Convertita` e `POST CALL` (oggi in bozza) sono il posto naturale per la cadenza qui sopra.

## 8. Blocco 6: firmato, pagamento e avvio

```
 FIRMATO  (stato firma = firmato)
        |
        v
 PAGAMENTO ATTESO  (stato pagamento = atteso)
   verifica incasso: un bonifico "citato" non e un incasso
        |
        +-- ricevuto ---> CLOSED  (definizione di Closed da decidere, vedi sotto)
        |                    |
        |                    v
        |             ONBOARDING (call di setup): requisiti, zona, canale di consegna,
        |                    |    contatto operativo
        |                    v
        |             AVVIO CAMPAGNE ---> primi contatti (tempi concordati col cliente;
        |                                 nessuna scadenza garantita in generale)
        |                    |
        |                    v
        |             PACCHETTO COMPLETATO ---> riacquisto da valutare
        |
        +-- non arriva ---> verificare, non dichiarare avviato; task
```

**Decisione aperta:** oggi "Closed" in GHL include contratti firmati senza incasso (Testanera risulta Closed/won ma dalla call aveva solo un contratto da inviare). Proposta: Closed solo a pagamento ricevuto; prima resta in Proposal Sent con stato firma = firmato e pagamento = atteso.

## 9. Blocco 7: perso, rinviato e riattivazione

```
 PERSO / RINVIATO  (sempre con motivo + data di ricontatto o chiusura)
        |
        v
 motivo                    ---> riattivazione                                [PROP]
 -----------------------------------------------------------------------------------
 timing (data data dal lead)    task alla data; un solo messaggio
 decisore                       data del decisore; proporre call con tutti
 prezzo                         dopo 30 giorni, solo se il lead lo chiede o cambia
                                 la situazione (nessuno sconto anticipato)
 pagamento-anticipato           solo se cambia la regola; altrimenti archivio
 concorrente                    dopo 60-90 giorni
 esperienza-passata             dopo 30 giorni, con un caso documentato (se esiste)
 silenzio-post-call             1 messaggio di chiusura, poi 60 giorni
 non-raggiunto                  dopo 60 giorni
 fuori-target / rifiuto         nessuna azione, archivio
```

## 10. Segnali di qualità a Meta (con Facebook come fonte principale)

Dalla struttura usata nell'altra location Mailift, e da verificare se esiste anche qui:

```
 stage              evento verso Meta      note
 ----------------   -------------------    ------------------------------------------
 NEW LEAD           nessuno                segnale troppo sporco (non qualificato)
 FISSATA CALL       Schedule               solo se non marcato come non qualificato
 PROPOSAL SENT      Lead (qualificato)
 CLOSED (pagato)    Purchase               con il valore del pacchetto
```

Nessuno degli 8 flussi risulta fare questo `[VER]`.

## 11. Collegamento tra stage e campi LOD

| Stage | Campo Esito | Altri campi aggiornati |
|---|---|---|
| New Lead | (vuoto) | fonte Facebook, dati del modulo |
| Contacted | non-raggiunto, rinviato, perso | data ricontatto, tipo ricontatto, motivo, passi prequalifica |
| Fissata call | call-fissata, no-show | ultima call data e tipo |
| Proposal Sent | proposta-inviata, rinviato, perso | stato firma, pacchetto, zona, voti, obiezione |
| Closed | firmato-attesa-pagamento, pagato | stato firma, stato pagamento |

## 12. Cosa non ho potuto vedere

- I passaggi interni dei 6 flussi pubblicati: trigger, attese, condizioni. L'API restituisce solo nome e stato. Servono gli screenshot di ogni flusso per completare i `[VER]`.
- Se il passaggio da New Lead a Contacted e da Contacted a Fissata call è automatico o manuale.
- Il testo completo degli SMS e delle email automatiche (ho visto i modelli, non il contenuto intero).
- Se il modulo Facebook è un lead form istantaneo o una landing.
