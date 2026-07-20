# Call: Analisi ads Mailift + valutazione progetto pay-per-lead

**Data:** 2026-07-20
**Partecipanti:** Lorenzo Baretta, Fabio
**Durata:** 60 min
**Registrazione:** https://fathom.video/share/KthoQGso_zPV4wYMA458wvfT9eNbUsK8

## Riassunto esecutivo
Due blocchi. Primo: review dell'account ads Mailift — struttura di test creativi, scelta dell'evento di ottimizzazione (CompleteRegistration invece di Lead per non ottimizzare su lead fuori target), qualità lead dal quiz e automazione creative via Manus+Claude. Secondo: valutazione del progetto PPL con Fabio — modello, pricing, prerequisiti sul cliente, roadmap. Decisione: lancio PPL a settembre, agosto per costruire offerta e trovare 1 cliente test dal network.

## Decisioni prese

### Ads Mailift
- Ottimizzare le campagne su **Registrazione completata**, non su Lead: passare l'evento Lead su contatti non qualificati rischia di far ottimizzare Meta su un target fuori mercato. Per avere l'evento disponibile in campagna si è usata la colonna opportunità.
- Struttura test confermata: una campagna "banca test futuri" con i creativi in coda, mini-test da 3 creativi × 2 headline × 2 copy per angolo; il **winner viene duplicato in una campagna separata** (come la "gialla", angolo loss aversion) e da lì si declina in carosello / video UGC.
- CTA da cambiare: `Vedi dettagli` → **`Scopri di più`** (feedback Fabio). Resto della campagna ok.
- **Quiz: rimuovere la squalifica hard sul fatturato.** Tutti completano il quiz e restano in DB; l'evento CompleteRegistration viene inviato via API **solo** se il fatturato è sopra soglia. Logica di Fabio: raccogli il contatto comunque, ottimizzi solo sui buoni.
- Aggiungere dedupe sul nome (oggi viene chiesto due volte).
- Le Rive: **staccare le campagne il 31 luglio** (non prima).

### Progetto PPL
- Si parte da **un settore alla volta** — fotovoltaico — non tre in parallelo.
- **Lancio a settembre.** Agosto è morto: si usa per offerta, setup e ricerca cliente test.
- Primo test su **1 solo cliente** preso dal network (BNI, conoscenti, contatti di Riccardo), venduto a copertura costi, non a margine: serve a misurare il CPL qualificato reale.
- Modello di pricing di partenza: **pacchetto 20 lead = €1.000** (~€50/lead), con CPL target €20 → **€400 di ads, €600 di margine**. I €400 vengono reinvestiti in ads.
- Il modulo lead di Facebook si usa in partenza; landing dedicata solo quando il sistema funziona (Lorenzo si aspetta qualità migliore da landing, Fabio pensa cambi poco).
- **Prerequisito di vendita**: il cliente deve avere un processo di vendita. Se non ce l'ha, i lead non convertono comunque → diventa un upsell, non una obiezione.

## Action items

### Lorenzo / Mailift
- [ ] Quiz: rimuovere il filtro fatturato, aggiungere dedupe nome, inviare CompleteRegistration via API solo sopra soglia
- [ ] Flusso lead parziali: email passata dal popup al quiz via URL → webhook su abbandono → Make → GHL con tag `parziale`, + automazione di follow-up gestita da AI
- [ ] Cambiare CTA in `Scopri di più`
- [ ] Cercare il tool di lead delivery con routing per zona e cap per cliente (nome non ricordato in call)
- [ ] Scrivere offerta PPL + listino: pacchetto lead, pacchetto CRM/setup, pacchetto ore consulenziali sul processo di vendita
- [ ] Valutare inquadramento fiscale del progetto PPL (SRL esistente vs newco)
- [ ] Le Rive: staccare campagne il 31/07
- [ ] Chiudere il video con Mark Zuckerberg (rischio blocco creatività: personaggio pubblico)

### Fabio
- [ ] Verificare se ci sono contatti nel network BNI utilizzabili come primo cliente test
- [ ] Portare il suo storico fotovoltaico (CPL, tassi, domande di screening) come baseline

## Contesto aggiornato

**Ads Mailift / funnel quiz**
- Dal 1 luglio: 17 contatti, CPL ~€21 (in discesa), 2 lead perfettamente in target — ma i 2 buoni arrivano da **campagne vecchie che sono state cancellate**, non dalle nuove. CPL su lead qualificato: €179,45.
- Stamattina 3 contatti, tutti squalificati alla domanda fatturato e dirottati sul lead magnet → da qui la decisione di togliere il filtro.
- Automazione creative attiva: analisi settimanale delle creative performanti → Manus genera varianti → Claude le carica in account. Sta già producendo creative in campagna, performance ancora da verificare.

**Progetto PPL — economia del modello (dati Fabio)**
- Nel fotovoltaico con **2 sole domande** di screening: CPL €9-10, ma su 90 lead solo ~3 utilizzabili — il resto sono fuori target (molti cercano di affittare terreni, non di installare).
- Con **5-7 domande** di qualifica: CPL sale a €20-25 ma il lead è ultra-qualificato e rivendibile a €70-80. Il volume cala, il valore per lead sale molto. Limite: oltre ~7 domande si entra nel tecnicismo e si perde compilazione.
- Fabio ha 5 angoli validati nel fotovoltaico (uno preso da Reddit, uno sulle top 30 aziende italiane del settore); un'inserzione ha fatto 80 lead in un mese e mezzo.

**Visione di lungo periodo**
- Costruire un **comparatore multi-settore** stile Facile.it (fotovoltaico, clima, caldaie, assicurazioni) con campagne su proprietà Mailift, non sulle pagine dei clienti. Permette di riassegnare a un partner diverso il lead non interessato al primo.
- Pacchetti annuali (20 lead/mese garantiti per 12 mesi) come strumento di ricorrenza.

## Segnali importanti
- **Giuseppe** (eCommerce white label, ~€20k/mese): contratto mandato, gli è piaciuta la proposta, ma il suo team aveva già fissato appuntamenti con altre agenzie → firma sospesa. Non è una questione di prezzo: non conosce il mercato e vuole confrontare. Lorenzo ha lasciato la porta aperta. **Da ricontattare.**
- **Stefano**: contratto anche per lui, stato da verificare.
- Attrito con il collaboratore/cliente che ha **cancellato campagne** dall'account: ha eliminato proprio le campagne che portavano i 2 lead buoni. Lorenzo gliel'ha contestato e ha ricordato i €15.000 in sospeso per luglio; risposta: "tra dieci giorni, sono in ferie".
- Punto di rischio del modello PPL identificato da Lorenzo: **il prezzo di vendita del lead è l'unica variabile che può far saltare i conti** (troppo alto = non vende, troppo basso = non copre). Fabio propone di partire da €50/lead e scalare.

## Note operative
- Angolo creativo che sta funzionando meglio: **loss aversion** (la "campagna gialla"). Il creativo vincente ha stile "vecchia scuola" ma CTR alto.
- Idea creativa in lavorazione: video di Mark Zuckerberg che afferma che smettere di fare ads a favore del marketing organico danneggia il concorrente — alto potenziale di attenzione, rischio di blocco.
- Sulla condivisione lead nel PPL: Lorenzo proponeva di rivendere lo stesso lead fino a 3 volte in zone diverse; **Fabio è contrario** — preferisce campagne divise per città con più clienti per zona, così il budget resta concentrato e Meta ottimizza meglio. Punto **non ancora chiuso**.
- Sul cap volumi: spegnere la campagna a raggiungimento quota fa ripartire l'apprendimento da zero. Meglio un processo di **upsell preventivo** ("stiamo per arrivare al limite, vuoi altri lead?") che uno spegnimento.

## ⚠️ Da verificare
La soglia di squalifica citata in call è **€15k**, ma il codice del quiz (sessione del 20/07) usa **€10k**. Prima di implementare il CompleteRegistration condizionale, confermare quale soglia vale.
