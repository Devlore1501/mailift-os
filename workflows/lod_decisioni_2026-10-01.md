# Lead on Demand: decisioni e note del 1–2 ottobre 2026

Raccolta di quanto deciso nella sessione di lavoro. Non contiene dati personali dei prospect né credenziali. I file operativi collegati sono `workflows/lod_weekly_call_review.md`, `workflows/lod_sales_process.md`, `knowledge/lod-script-prequalifica-installatore.md`, `tools/lod_ghl_schema.py`, `tools/lod_review_apply.py`.

## 1. Prezzi e trattativa

- Costo di un lead qualificato nella zona Nord-Ovest: 80 euro (dato di Lorenzo). Con prezzo di vendita 150 euro il margine lordo è 70 euro a lead, con 180 euro è 100 euro, prima dei costi fissi.
- Proposta per il pacchetto di prova da 10 lead: 180 euro più IVA a lead, ripiego a 160 euro, nessuna offerta sotto 160. Il pacchetto da 5 lead solo a 200 euro e solo come concessione.
- Lorenzo mantiene il controllo della trattativa: il prezzo lo fissa lui, il cliente non detta le regole. Nessun accenno scritto a sconti o incentivi; lo sconto sui volumi si spiega a voce.
- Fasce dichiarate in prequalifica: residenziale 100–130 euro a lead, aziende 150–200 euro e oltre. In chiamata si dicono le fasce per capire se il servizio ha senso, l'offerta si presenta solo a chi è interessato.

## 2. Tono dei messaggi di riattivazione

- Posizionamento: sono loro ad aver richiesto le informazioni; Lead on Demand lavora con esclusiva di zona; la disponibilità della zona va verificata; nessun inseguimento; nessuna scarsità inventata.
- Da evitare: formule tipo "quando hai sentito... scrivimi senza fretta" e toni troppo diretti. Chi è interessato deve muoversi lui.
- Leva "altre richieste per quella zona": usarla solo se verificata. Per il caso di Ignazio sono pronte la versione A (con la leva) e la versione B (onesta, senza leva non verificata).
- Prima di scrivere a un contatto: controllare la cronologia già inviata (email, chiamate, messaggi) per non duplicare.
- Mattina del 5 ottobre: messaggio di chiusura a Tiziano e email a Falsetti (slot proposti martedì 6 ottobre alle 10:00 e alle 16:30).

## 3. Socio e ripartizione degli utili

Contesto: Lorenzo ha creato tutto (marchio, offerta, CRM, automazioni, processo di vendita, script, contratti, knowledge base), gestisce prequalifica, formazione del team commerciale, trattative, follow-up, contratti, upsell e cross-sell, e anticipa il budget ads. Il socio, part-time con altri clienti, gestisce le ads di Lead on Demand, creative e copy, campagne e costo per lead, consegna e sostituzioni. Compenso previsto solo come quota sugli utili. Uscita non discussa. Asset misti: ad account dei clienti di Lorenzo, ad account di Lead on Demand del socio.

Parere dato: il 50% è troppo alto. Struttura proposta:

1. Fee di vendita a Lorenzo del 10–15% dei ricavi di ogni pacchetto chiuso, prima dell'utile (cifre di riferimento di Lorenzo, non dati di mercato).
2. Sull'utile residuo: 70% a Lorenzo e 30% al socio all'inizio, con salita fino al 40% dopo 12 mesi se vengono rispettate soglie (costo per lead, tasso di sostituzione, tempo dedicato). Se il socio fosse con Lorenzo dall'inizio e avesse contribuito all'offerta, la quota potrebbe stare tra il 40 e il 45%.
3. Tutto ciò che Lorenzo ha creato resta di Mailift: marchio, dominio, CRM, automazioni, script, contratti, knowledge base, clienti e dati. Gli asset ads di Lead on Demand vanno in un Business Manager separato intestato a Mailift.
4. Quota anche su upsell e cross-sell nati dai lead portati dalle ads.
5. Vesting della quota e clausola di uscita: restano al socio solo i pacchetti già avviati per 6–12 mesi, con patto di non concorrenza.
6. Test di riferimento: quanto costerebbe sostituire il socio con un freelance o un'agenzia per le ads. La quota non dovrebbe superare di molto quel costo.

Dati ancora mancanti per il calcolo di un pacchetto da 20 lead: costo del team di prequalifica per contatto, costo ads per lead qualificato (80 euro vale anche fuori Nord-Ovest?), numero di pacchetti al mese previsti nei primi sei mesi, budget ads mensile. Da preparare poi una scheda di una pagina con ruoli, formula e clausole, da far rivedere al commercialista. Per la forma giuridica serve un professionista.

## 4. GHL: modifiche fatte e da fare

Fatto il 2 ottobre 2026 (modulo Facebook istantaneo per i clienti finali aziende):

- Creati due campi contatto a scelta singola nella cartella "Qualifica": "Lead cliente: spesa energia mensile azienda" (1.000–3.000 €, 3.000–10.000 €, oltre 10.000 €) e "Lead cliente: titolare o responsabile decisionale" (sì / no).
- Nome, e-mail e telefono sono campi standard e non servivano.
- L'API non permette di creare cartelle per i campi contatto: una cartella dedicata va creata a mano da Impostazioni, Campi personalizzati.
- Il modulo ha altre domande oltre alle tre viste (barra al 75%): servono gli altri screenshot.
- La mappatura dal modulo Facebook ai campi va fatta nel workflow GHL che riceve il lead.

Da fare:

- I 19 campi "LOD ..." per la review delle call non sono ancora stati creati: `python tools/lod_ghl_schema.py --apply` dopo approvazione.
- Scrittura dei risultati della review sui contatti (`tools/lod_review_apply.py`) solo dopo anteprima e conferma.
- Decidere la definizione di "Closed" (firmato oppure pagato) e correggere il fuso orario (Amsterdam invece di Roma).
- Valutare l'attivazione dei due workflow in bozza (POST CALL e Follow-Up Presentazione Non Convertita), correggere l'SMS in inglese nel workflow contratto, verificare il testo del promemoria "rispondi per confermare altrimenti verrà cancellato", inviare gli eventi CAPI a Meta.

Credenziali GHL: non sono salvate nel repository né nella sessione. Il client le legge da `~/.secrets/mailift/.env` oppure da `.env`, che in questo ambiente non esistono. La chiave condivisa in chat andrebbe ruotata.

## 5. Verifiche aperte

- Testanera: stato Closed/won con contratto non firmato?
- IMATFELCO: esito della seconda call del 30 settembre alle 16:30 (in conflitto con la call di Ignazio).
- Altamura: richiamata alle 14:30 del 1 ottobre in conflitto con l'evento "scv imprenditori" delle 14:00–15:05.
- Roberto Breddo: richiamata.
- Tiziano: stato del contratto nella sezione Documenti di GHL.
- Nardiello: verificare se la Campania residenziale è coperta prima del messaggio.
- Titoli Fathom da uniformare con "LOD" (una call di Marco Mochi non è taggata).
- Notion: database e pagina riepilogo da creare quando il connettore è disponibile.
- Miro: eliminare a mano le due board vecchie (uXjVEfkwuZE=, uXjVEfkL0AY=); la board finale è uXjVEfriJVY=.
