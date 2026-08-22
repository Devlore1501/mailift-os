# Handoff — Strategia Contenuti Social & Video Mailift

*Ultimo aggiornamento: 2026-08-06 · Owner: Lorenzo Baretta · Stato: in produzione*

> Documento di passaggio di consegne. Cosa è stato deciso, cosa è stato prodotto, cosa resta aperto.
> **Se riprendi il lavoro da qui, la cosa più veloce è invocare la skill `mailift-social-strategy`**: contiene tutto il metodo in forma operativa. Questo documento serve a capire lo stato delle cose.

---

## 1. Il vincolo che governa tutto

Mailift è un servizio done-for-you a **capacità limitata**: servono ~3 nuovi clienti al mese, non 300.000 follower. La reach non è il collo di bottiglia, lo è **l'accesso al buyer giusto**.

Conseguenza pratica: un video da 400 views che porta due DM da titolari eCommerce ha battuto un video da 40.000 views che non ne porta nessuno. Questo criterio va applicato a ogni decisione.

---

## 2. Buyer persona

Titolare-operatore di **eCommerce DTC su Shopify, 50-200k€/mese**, dipendente dalle Meta ads, con una lista di migliaia di contatti non monetizzata. **Problem-aware ma NON solution-aware.**

Tre porte d'ingresso emotive: **il Sovraccarico** · **il Drogato di Ads** · **il Bruciato dalle agenzie**.

Dettaglio e citazioni reali: `ricerca-mercato-buyer-persona.md` e `voice-of-customer-ads-bank.md`.

---

## 3. I due assi (non confonderli)

Questa distinzione è stata la correzione più importante della sessione.

**Asse obiettivo** — cosa deve *fare* il contenuto:
- **Attrazione**: pratico, risolutivo, si salva e si applica. Micro-argomento.
- **Consapevolezza**: NON risolutivo per scelta, crea il gap "sì, ma come lo faccio io?". Macro-argomento.
- **Vendita**: diretta o indiretta.

**Asse consapevolezza pubblico** — quale sostantivo nomini:
- **BOF** = lo strumento · **MOF** = il metodo · **BROAD** = il risultato desiderato.

Nel broad la parola "email" non compare mai. Analogia di riferimento: squat (BOF) / allenamento gambe (MOF) / chiappe sode (BROAD).

**Errore da evitare:** pensare che broad = attrazione. Sono assi indipendenti.

---

## 4. I tre framework integrati

| Strato | Fonte | Domanda |
|---|---|---|
| Sostanza | Callaway | pain point → soluzione novel → trust |
| Mira | Alexa | broad-for-pipeline vs niche · pronto-ora vs pronto-presto |
| Distribuzione | Kevin (Grow The Show) | algoritmo · collaborazioni · diretto |

**Priorità distribuzione per Mailift:** diretto e collaborazioni ORA (accesso concentrato), algoritmo come gioco lungo.

---

## 5. Strutture di script (tre famiglie)

1. **8 beat** — Hook · Promise · Body1 · Loop1 · Body2 · Loop2 · Body3 · CTA. Tiene con la curiosità. 60 sec ≈ 190 parole, 30 sec ≈ 90.
2. **Formati a raffica** (15-30 sec) — Frame → 3-5 unità indipendenti → chiusura. Tiene con la densità. Cinque pattern: smetti/inizia · se vuoi X fai Y · non è X è Y · rapid fire errori · ogni volta che. Richiedono ritmo visivo a ogni riga o collassano.
3. **Perfect Yap** (5 blocchi) — hook con negative framing · curiosity gap energico · storytelling con valore tattico dentro · social proof con pacing · CTA spiritosa. Più adatta al parlato, ma richiede consegna energica: se la leggi piatta, crolla.

**Regole hook:** deve accusare, minacciare o contraddire. Mai introdurre. Se puoi cancellare le prime tre parole senza perdere niente, riscrivilo.
**Nemico numero uno:** i concetti appesi (etichette vuote tipo "segmentazione avanzata").
**L'hook si sceglie per ultimo**, salvo quando si parte da una reference.

---

## 6. Piano editoriale attivo

**`piano-editoriale-mese1.md`** — 16 contenuti, 4 a settimana, mix **75% attrazione / 25% consapevolezza** (profilo "aumentare il movimento", corretto per una partenza da zero).

Ritmo: Lun · Mer (consapevolezza fisso) · Ven · Dom.

⚠️ `calendario-contenuti-30gg.md` è **superato** (usava un mix 50/30/20).

### Stato produzione

**6 video già girati** (dalla prima versione del calendario):

| Girato | Slot nel piano | Note |
|---|---|---|
| Meta / affitto | #2 | hook vecchio, da sostituire |
| Deliverability | #4 | serve rigirare hook + promise insieme |
| Welcome flow | #3 | hook vecchio |
| Segmentazione | #7 | hook vecchio |
| My story 15k | #10 | hook vecchio |
| Case study calo 40% | fuori piano | jolly / primo BOF del mese 2 |

**Restano 11 da girare.** Il prossimo necessario è **#1 — Carrello abbandonato**.

**Fix consigliato sui 6 girati:** rigirare solo l'hook (5 secondi) e montarlo davanti. Gli hook nuovi sono in `script-templates.md`. Se rigirare fa slittare la pubblicazione di più di qualche giorno, pubblicare come sono: la costanza vale più della perfezione.

---

## 7. Materiali prodotti

| File | Contenuto |
|---|---|
| `piano-editoriale-mese1.md` | il piano attivo a 16 contenuti |
| `testi-mese1-script-e-didascalie.md` | 16 script completi + 16 didascalie |
| `content-bank-reel-quickwin.md` | 13 script quick-win |
| `script-12-video-mese1.md` | i 12 script della prima versione |
| `ricerca-mercato-buyer-persona.md` | ricerca di mercato + VOC + dati flaggati |
| `voice-of-customer-ads-bank.md` | 75 call reali, citazioni verbatim |
| `calendario-contenuti-30gg.md` | ⚠️ superato |

**Pagina web pubblicata** (leggibile da telefono, didascalie copiabili):
https://claude.ai/code/artifact/749bf529-cc83-42ba-8164-dac874c8549d

**Didascalie alternative scritte in chat** (non ancora nei file): versione "cosa mandare a ogni segmento" per il video segmentazione · versione "l'invisibilità del problema" per deliverability · versione "cosa scrivo al posto dello sconto" per carrello · yap sulle disiscrizioni con caption.

---

## 8. La skill `mailift-social-strategy`

In `.claude/skills/mailift-social-strategy/` — è il cervello del sistema, si attiva da sola quando si parla di contenuti.

| File | Contenuto |
|---|---|
| `SKILL.md` | vincolo, ICP, strategia, assi, strutture, regole, guardrail |
| `references/framework-contenuti.md` | i 3 strati |
| `references/voice-of-customer.md` | persona + citazioni + pain/baseline/soluzione |
| `references/piano-editoriale.md` | attrazione/consapevolezza, macro→micro compilato, formati, mix |
| `references/processo-scripting.md` | 4 principi, processo in 6 passi, metodo reference |
| `references/script-templates.md` | 8 beat, formati a raffica, regole hook e caption |
| `references/banca-hook.md` | ~40 hook per 9 leve + pattern da evitare |

**Esportazioni fatte:** versione monolitica completa, versione ridotta per un agente copywriter (752 righe). Se la skill viene aggiornata, vanno rigenerate.

---

## 9. Guardrail (non negoziabili)

Il buyer è **già stato bruciato dalle agenzie**: con lui la cautela costruisce più fiducia dell'entusiasmo.

- Mai case study inventati o brand famosi spacciati per clienti. La versione legittima è il teardown dichiaratamente ipotetico.
- Nei teardown si critica il lavoro, mai la persona.
- Dati dei clienti: solo numeri reali e verificati, con ok del cliente se il brand è riconoscibile.
- Vietati gli hook da guru ("cheat code", "tattiche non etiche", "il top 0,1% non vuole che tu lo sappia").
- **Claim da verificare prima dell'uso in ads a pagamento:** benchmark popup 6-8% · revenue email 25-30% · 7 carrelli su 10 · regola 20/80 VIP · CPM Meta +20% YoY · il conteggio delle call (75 lette in banca VOC).

---

## 10. Aperto — da fare

**Risorse promesse nelle CTA che non esistono ancora.** Se una CTA promette una risorsa e la risorsa non c'è, con questo pubblico il danno è superiore al beneficio:
- [ ] **Checklist deliverability** (CTA INBOX)
- [ ] **50 idee di email senza sconti** (CTA LISTA)
- [ ] Le altre risorse per keyword: CARRELLO, WELCOME, SEGMENTI, RIACQUISTO, WINBACK, POPUP, VIP, BROWSE, PULIZIA, OGGETTO, RIORDINO

**Produzione:**
- [ ] Rigirare i 6 hook e montarli
- [ ] Girare gli 11 contenuti mancanti (batch in 2 sessioni)
- [ ] Scrivere il contenuto #14 se non coperto

**Backlog:**
- [ ] 50 idee di contenuto sui 5 pilastri (scritte in chat, da salvare in un file)
- [ ] Censire 5-10 gruppi FB / hashtag / podcast **italiani** dove sta il buyer
- [ ] Verificare alla fonte i dati di mercato

**Sistemi:**
- [ ] Agente copywriter su Paperclip (istruzioni e KB già scritte in chat)
- [ ] Agente analista social (istruzioni scritte; richiede un livello di raccolta dati — Apify + filtro anomalia + Whisper, orchestrabile in n8n che è già nello stack)

---

## 11. Misurazione

Non le views. **DM e commenti con parola chiave**, salvataggi, compilazioni del questionario.

La keyword più richiesta indica il dolore più vivo e guida il mese 2. Il salvataggio è la metrica-chiave dei contenuti di attrazione: se non si salvano, non erano risolutivi.

**Alla fine dei 30 giorni:** se il movimento cresce, sposta il mix verso 40/40/20. Se resta basso, resta su 75/25 e lavora su hook e format, non sugli argomenti. Aggiungi **un solo** formato nuovo. I contenuti migliori diventano creative per il retargeting.
