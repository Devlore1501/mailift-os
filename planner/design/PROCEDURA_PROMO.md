# Procedura promo — Sale Strategy Mailift

> Procedura operativa per le sale, testata su 30+ brand. È la strategia che il
> generatore di piani applica automaticamente alle sequenze **promo** create nella
> sezione "Lanci & Promo" del catalogo brand (vedi `_SYSTEM` in
> `backend/app/services/claude_ai.py`). Questo file è la fonte: se la procedura
> cambia, aggiornare anche il prompt.

Non basta annunciare una sale: la maggior parte dei marketer manda solo l'annuncio,
qualcuno un follow-up, pochissimi la last-chance. Mescolando tutto questo con email
plain text, countdown, recensioni, best seller e segmentazione si ottiene una
strategia vincente riutilizzabile per ogni sale.

Una sale completa ha **5 fasi**:

1. Pre-Launch (teaser)
2. Launch (annuncio)
3. Follow-up
4. Last Chance
5. Final Reminder

---

## 🏁 1. Pre-Launch (teaser) — 1-3 giorni prima

È il riscaldamento prima della partita: costruire attesa e buzz prima di mostrare
il piatto forte. Funziona per qualsiasi sale "semplice" (Pasqua, estate, Halloween…
tutto tranne il Black Friday, che merita un trattamento a parte).

- Email hype **"Non comprare da noi (oggi)"**: consiglia di NON acquistare adesso
  perché sta arrivando una grande sale. Tocco personale, costruisce fiducia —
  nessuno è contento di comprare oggi e vedere lo sconto domani.
- Invita a **rispondere alla mail** per sapere della sale in anteprima: le risposte
  migliorano molto la deliverability (le email finiscono in primary/importanti
  proprio per chi è più interessato a comprare).
- **Countdown** all'inizio della sale per aggiungere attesa e urgenza.
- **NON rivelare lo sconto**: si svela solo al lancio.

## 🚨 2. Launch (annuncio) — giorno di inizio

Semplice e diretta: qui non si può sbagliare. Controlla i link, verifica che il
codice sconto funzioni, programma all'orario giusto.

L'email deve essere leggibile **a colpo d'occhio**, 4 elementi:

- **SALE SALE SALE** — header
- **15% OFF** — l'offerta in grande
- **SHOP SALE NOW** — call to action
- **Tutto è in sconto** — una riga di info

Si può aggiungere una griglia di prodotti consigliati, ma l'impatto è marginale.

## 🎁 3. Follow-up — a giorni alterni

La fase che quasi tutti saltano: **non mandarlo è lasciare soldi sul tavolo**.

- Sale di **5 giorni** → follow-up il **giorno 3**.
- Sale di **7 giorni** → follow-up i **giorni 3 e 5**.
- Regola generale: qualcosa sulla sale **ogni due giorni** se dura più di 3 giorni.

Il follow-up non deve solo urlare di nuovo la sale, ma aggiungere contenuto:

- **best seller / prodotti consigliati** (la gente compra ciò che comprano gli altri),
- **recensioni** (fiducia + social proof),
- **email plain text stile "customer support"** → è quella che **converte meglio**:
  sembra scritta da una persona vera, può includere recensioni e best seller.

## 🔥 4. Last Chance — mattina dell'ultimo giorno

A volte performa **meglio del lancio**: urgenza + scarsità. Tre ingredienti:

- **countdown** alla fine della sale,
- copy di **urgenza e scarsità**, risparmio evidenziato in grande,
- **best seller**.

Programmarla **la mattina**, per lasciare spazio al final reminder.

## ⏰ 5. Final Reminder — sera dell'ultimo giorno (<5h alla fine)

Ultima spremuta, solo al segmento più caldo:

- **Segmento**: chi ha **cliccato** le email della sequenza ma **non ha acquistato**
  (escludere gli acquirenti degli ultimi 20 giorni per non colpire chi ha già comprato).
- **Formato plain text**: converte tantissimo su questo pubblico.
- Il **countdown** qui fa il grosso del lavoro: meno di 5 ore sul timer.

---

## Perché funziona

C'è un funnel pulito, mai troppo insistente ma che spreme tutto il possibile:

- l'hype costruisce attesa,
- il lancio dà il via,
- i follow-up ricordano la sale e mostrano prova sociale,
- la last chance crea scarsità e mostra i best seller,
- il final reminder spreme chi era davvero interessato.

## Adattamento alla durata

| Durata sale | Sequenza |
|---|---|
| **5-7 giorni** (ideale) | teaser → annuncio → follow-up (g.3, e g.5 se 7gg) → last chance → final reminder |
| **3 giorni** (weekend) | annuncio → last chance → final reminder (niente follow-up) |
| **48h flash** | annuncio → last chance → final reminder |
| **24h flash** | annuncio → last chance |

Cadenza: email a giorni alterni per non stressare la lista (eccezione: il final
reminder, che segue la last chance nello stesso giorno).

## Come si usa nell'app

1. Catalogo brand → tab **Lanci & Promo** → nuova voce di tipo **promo** con date
   di inizio/fine (la durata determina la sequenza secondo la tabella sopra).
2. Genera il piano del mese: le email della sequenza compaiono etichettate con
   nome sale + ruolo (teaser, annuncio, follow_up, last_call, final_reminder) e
   contano nella quota promo della regola 70/20/10.
3. In cima al piano trovi la **spiegazione della strategia** scelta e le
   **proposte extra** (countdown, estensione VIP, SMS…).
4. I ruoli e i segmenti (incluso "cliccato senza acquistare") arrivano anche su
   Notion nella colonna **Sequenza**.
