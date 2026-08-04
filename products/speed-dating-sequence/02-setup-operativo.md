# Speed Dating Sequence — Setup operativo

*Da leggere prima del primo invio. Il copy sta in `01-sequenza-completa.md`.*

---

## 1. Cosa è cambiato rispetto al brief iniziale (e perché)

Tre correzioni strutturali, tutte derivate da `knowledge/mailift-listino-pricing.md` e `knowledge/mailift-knowledge-base.md`.

| Nel brief | Nella versione scritta | Perché |
|---|---|---|
| Ascension "Fondazione Flow" a **€1.497** | **Email Foundation Setup a €2.000** (€1.953 scalando i €47) | Il prodotto esiste già a listino ed è pensato esattamente per questo segmento (corsia B, 8–25k€/mese). €1.497 era un prezzo inventato e sotto il floor di riferimento. |
| CTA ascension = **"prenota una call"** | CTA = **one-pager + link di pagamento**, call da 15 min come opzione secondaria | Il listino è esplicito: corsia B si vende in modo asincrono, max 1 call da 15 minuti, niente discovery. Una call obbligatoria rompe l'economia del prodotto. |
| Mappa a **8 flussi** in Email 4 | **6 flussi + pop-up + infrastruttura deliverability** | Deve coincidere con lo scope reale di Email Foundation Setup. Se Email 4 fa desiderare 8 cose ed Email 6 ne vende 6, l'offerta arriva già in debito. |

Altre modifiche minori:
- Gli esempi generici ("un ecommerce di integratori… 19%") sono stati sostituiti con **casi reali dalla VOC bank** (vedi §4).
- Email 0 non apre più con "Ciao" ma con la tensione, in linea con le regole del team copy.
- Aggiunta **F3** ai follow-up del €47 (chiusura onesta, senza finta scadenza).
- Aggiunto in Email 5 lo **split condizionale "ha già ordinato"**, che mancava e genera l'errore più fastidioso (mail "il tuo codice scade" a chi ha appena comprato).

---

## 2. Segmentazione — chi riceve cosa

**Email 0 va SOLO a:**
- lead **corsia B** (8–25k€/mese, Shopify, lista esistente) mai chiusi
- lead **corsia C** ancora vivi (troppo piccoli, ma con lista e prodotto)
- prospect persi da oltre 90 giorni che non sono in trattativa

**Email 0 NON va MAI a:**
- clienti attivi (retainer, setup in corso, pacchetto grafica)
- lead corsia A in target caldi → per loro vale la riattivazione diretta sul retainer, non un prodotto da €47
- chi ha una call già fissata

**Suppressione tecnica in GHL/Klaviyo:** crea un segmento di esclusione `NO_SPEED_DATING` con clienti attivi + corsia A + trattative aperte, e applicalo a tutti gli invii della fase 0.

---

## 3. Timing e trigger

### Fase riattivazione (lista fredda)
| Email | Invio | Condizione |
|---|---|---|
| Email 0 | Giorno 0 | Segmento corsia B/C meno esclusioni |
| F1 | +2 giorni | Ha aperto Email 0, non ha comprato |
| F2 | +4 giorni | Non ha comprato |
| F3 | +7 giorni | Non ha comprato |

**Re-permission.** Il P.S. di Email 0 è il filtro. Chi apre o clicca entra nel segmento "vivo". Chi non tocca nulla in tutte e quattro le mail → segmento dormiente da sunset. Le disiscrizioni qui sono un guadagno di deliverability, non una perdita.

### Fase prodotto (post-acquisto €47)
| Email | Invio |
|---|---|
| Email 1 | Immediato dopo acquisto |
| Email 2 | +24h |
| Email 3 | +48h |
| Email 4 | +72h |
| Email 5 | +96h |
| Email 6 | +120h (giorno 6) |
| Email 7 | +3 giorni da Email 6 |
| Email 8 | +3 giorni |
| Email 9 | +3 giorni |
| Email 10 | +4 giorni |

**Uscita dal flusso:** chi acquista Email Foundation Setup esce da Email 7-10.

**Nota sugli engagement ask.** Ogni email 1-5 chiede una risposta. Sono la metrica primaria e vanno **davvero lette e risposte** — è il ponte umano che rende vendibile l'ascension. Se non riesci a gestirle, riduci gli ask a due (Giorno 2: l'oggetto; Giorno 4: il numero di flussi attivi) invece di lasciarli tutti senza risposta.

---

## 4. Prove usate nel copy — provenienza

Tutte reali, prese da `knowledge/voice-of-customer-ads-bank.md`, anonimizzate per settore.

| Dove | Prova | Fonte |
|---|---|---|
| F2 | "Calo di stagione del 40%, i flussi hanno tenuto" | Treemme / Kali Shoes |
| Email 1, Email 4 | Pop-up allo 0,4% su 123.000 visite/mese, benchmark 6-8% | Farmacia Papa |
| Email 3 | ~200 risposte spontanee "mandamele comunque" | Bergamo Vini |
| Email 4, Email 9 | 31 add-to-cart → 12 checkout → 1 acquisto | Zampette |
| Email 4, Email 8 | "Stiamo facendo guadagnare Google più di quanto guadagniamo noi" | Davide Cosentino |
| Email 6, Email 8 | "Il secondo acquisto arriva a costo pubblicitario zero" / ads da 1k a 15k | Andrea, Le Rive |
| Email 7 | 60.000 contatti, "non ho tempo da dedicarci" | Giovanni, Camperflash |

**Regola applicata:** nessun nome cliente nel copy, solo settore o descrizione generica. Se vuoi usarne uno con nome e screenshot, chiedi il permesso — vale dieci volte tanto.

---

## 5. Claim da verificare prima dell'invio

Questi numeri sono nel copy. Sono tutti coerenti con la knowledge base, ma **due vanno confermati sui tuoi dati Klaviyo reali** prima di premere invio.

| Claim | Dove appare | Stato |
|---|---|---|
| "I flussi automatici fanno intorno al 70% della revenue email" | Email 0, Email 1 | ✅ Da KB §7 (Pilastro 2). Usabile. |
| "L'email dovrebbe fare il 25-40% del fatturato totale, nei brand che vedo fa meno del 10%" | Email 4 | ✅ Da KB §5. Usabile. |
| "Pop-up: benchmark 6-8%" | Email 1, Email 4, Email 6 | ✅ Da VOC bank. Usabile. |
| "La welcome è il flusso con il ritorno più alto per singolo iscritto" | Email 0, F1, Email 1, Email 5 | ⚠️ **Verifica su 3-4 account tuoi.** Se sui tuoi conti è il carrello abbandonato a rendere di più per iscritto, riformula in "uno dei due flussi con il ritorno più alto". |
| "Apertura della welcome spesso oltre il 50%" | Email 2 | ⚠️ **Verifica.** È vero nella maggior parte dei conti sani, ma se i tuoi stanno sotto, abbassa a "spesso sopra il 40%". |
| "Disiscrizione sotto lo 0,5% per email = non stai infastidendo" | Email 3 | ✅ Soglia di settore standard. |

**Nota:** il brief originale prometteva "welcome = 15-25% del fatturato email". L'ho **tolto** dal copy e sostituito con claim più difendibili. È un numero che varia troppo tra conti e ti espone a un cliente che ti mette davanti il suo 6%. La promessa del prodotto resta forte anche senza.

---

## 6. Decisioni ancora aperte (servono a te, non al copy)

**A. La garanzia dell'Email Foundation Setup.**
Nel copy c'è: *"se a 30 giorni i flussi non generano in revenue attribuita almeno il costo del progetto, continuiamo a ottimizzare gratis finché non ci arriviamo"*, con due condizioni (traffico stabile, flussi non modificati da terzi).

A €2.000 di prezzo e ~540€ di costo diretto il margine regge anche con un paio di casi di over-delivery all'anno. Ma è una promessa vera che devi voler mantenere. Se non ti convince, l'alternativa è togliere la garanzia e tenere solo la consegna in 2 settimane come rassicurazione. Il copy funziona anche senza — cambia solo il blocco 7 di Email 6.

**B. La pagina di destinazione dell'ascension.**
Email 6, 7, 8, 9, 10 puntano tutte a un one-pager con scope + tempi + link di pagamento + link opzionale per 15 minuti. **Quella pagina non esiste ancora.** È il vero blocco: senza, la sequenza non è spedibile oltre Email 5.

**C. Dove ospitare il prodotto €47.**
Le cinque email vanno consegnate come flusso post-acquisto. Serve: prodotto a €47 con checkout, tag "buyer speed dating" che triggera il flusso, e la lista/segmento dedicato.

---

## 7. KPI — metrica primaria = reply rate

| Fase | Metrica | Riferimento |
|---|---|---|
| Email 0 | Open · click · **reply** | Il reply è il segnale di "vivo", conta più del click |
| Vendita €47 | Conversione all'acquisto | 1-3% sulla lista dormiente riattivata è un buon risultato |
| Email 1-5 | Completion rate + reply per email | Gli engagement ask alzano tutto il resto |
| Ascension | Vendite Email Foundation Setup ÷ acquisti €47 | Qui si decide il ROI dell'intero sistema |
| Email 7-10 | Conversione ritardata | Storicamente oltre metà delle conversioni arriva dopo il primo invito |

**Numero da guardare per primo:** vendite Email Foundation Setup ÷ acquisti €47. Se è sopra il 5%, il €47 non è un prodotto — è il miglior canale di acquisizione che hai, perché ti porta lead già formati, già in relazione e con un risultato ottenuto insieme.

---

## 8. Checklist pre-lancio

- [ ] Costruire il one-pager Email Foundation Setup (scope, tempi, prezzo, pagamento, link 15 min)
- [ ] Creare il prodotto €47 con checkout e tag buyer
- [ ] Costruire il flusso di consegna (Email 1-5) su Klaviyo/GHL
- [ ] Costruire il segmento corsia B/C + il segmento di esclusione `NO_SPEED_DATING`
- [ ] Verificare i due claim segnati ⚠️ in §5
- [ ] Decidere se tenere la garanzia (§6A)
- [ ] Testare tutti i link e i due prezzi (€47 e €1.953)
- [ ] Mandare Email 0 a un campione di 200 contatti prima del blast completo
