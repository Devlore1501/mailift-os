# MAILIFT — LISTINO & REGOLE DI PRICING
*Documento interno · v1.1 · Luglio 2026*

> Riferimento per preventivi. Tutti i prezzi derivano da due regole fisse (§6).
> Non scendere sotto i prezzi minimi senza ricalcolare il margine.
>
> **v1.1 (lug 2026):** aggiunte §10 (Grand Slam Offer & Garanzia ROI 3x) e §11
> (Unit Economics & Money Model). Le §1–9 restano il listino operativo; le §10–11
> sono il livello strategico che governa *come* si impacchetta e si difende il prezzo.

---

## 1. SETUP ONE-OFF — "Email Foundation Setup"

**Per chi:** lead fuori target per il retainer (8–25k€/mese) o brand senza email marketing attivo.
**Scope fisso (no custom):** infrastruttura deliverability (DNS, DKIM, SPF, DMARC) + 5 flussi core (Welcome, Abandoned Cart, Abandoned Browse, Abandoned Checkout, Post Purchase, Winback) + pop-up. Delivery 2 settimane via SOP, eseguito dall'AM.

| Configurazione | Prezzo | Costo diretto | Margine |
|---|---|---|---|
| Mono-lingua | **2.000€** | ~540€ (10–12 grafiche × 20€ + 300€ AM) | 73% |
| Per lingua aggiuntiva | **+600€** | ~0€ (Canva translate) + 30–50€ proofreader | ~90% |
| Esempio: 5 lingue | **4.400€** | ~740€ | ~83% |

**Leva di chiusura consentita:** dalla 3ª lingua in su, 500€/lingua. Mai sotto.
**Incluso nel prezzo per lingua (e da dire in preventivo):** copy dedicato, template, segmenti per locale, revisione madrelingua di subject, CTA e headline.
**Vendita:** asincrona — sequenza WhatsApp + one-pager + link pagamento (max 1 call da 15 min). Niente discovery call.

---

## 2. REBUILD ONE-OFF — per chi fa già email (male)

**Per chi:** brand con email attiva ma sotto-performante (flussi sbagliati, segmenti assenti, template da rifare). È il ponte obbligato prima del retainer: **mai fare il rebuild gratis dentro i primi mesi di retainer.**

| Configurazione | Prezzo | Note |
|---|---|---|
| Rebuild mono-lingua | **1.500–2.000€** | Sconto vs setup solo se infrastruttura già a posto |
| Per lingua aggiuntiva | **+600€** | Stessa regola del setup |

**Vendita:** parte sempre dal Revenue Leak Audit in versione teardown — performance attuale del cliente vs benchmark (email dovrebbe fare 25–40% del fatturato). Disarma l'obiezione "le email le facciamo già".

---

## 3. RETAINER — gestione continuativa

**Per chi:** in target (25k€+/mese su Shopify). Sempre preceduto da setup o rebuild.

| Configurazione | Prezzo/mese | Costo diretto/mese | Margine |
|---|---|---|---|
| Mono-lingua (~10 campagne) | **2.000€** | ~500€ (grafiche + 300€ AM con PED) | 75% |
| Per lingua aggiuntiva | **+300–400€** | ~0€ + proofreading | ~90% |

---

## 4. PACCHETTO GRAFICA — sola produzione

**Per chi:** brand che fanno PED e copy internamente; il nostro grafico produce le grafiche e le carica nel loro PED. Nessun coinvolgimento AM/strategia.

| Configurazione | Prezzo | Costo diretto | Margine |
|---|---|---|---|
| Standard (min 20 grafiche) | **70€/grafica** → min 1.400€ | 20€/grafica | 71% |
| Volume (40+ grafiche) | **60€/grafica** | 20€/grafica | 67% |
| Per lingua aggiuntiva | **+15€/grafica** | ~0€ (Canva translate) | ~95% |

**Regole anti-de-standardizzazione:**
- 1 giro di revisioni incluso; revisioni extra 20€/grafica.
- Brief scritto dal cliente; niente call di brief ricorrenti (oltre la prima).

**Valore strategico — porta d'ingresso al rebuild:** questo cliente è per definizione un "fa già email ma male" (corsia rebuild). Lavorando nel loro PED vediamo da dentro calendario, copy e gap. **Trigger GHL a 90 giorni dal primo ordine → proposta Revenue Leak Audit → Rebuild + Retainer.**

---

## 5. OPZIONE PERFORMANCE (rev-share)

**Quando proporla:** prospect scettici ("ho già provato con un'agenzia") o brand con forte potenziale di crescita.

**Formula:** fee fisso ridotto **1.200–1.500€/mese** + **10–15% sulla revenue email incrementale sopra baseline**.

**Regola critica — la baseline:** media della revenue email degli ultimi 3 mesi, fissata dall'audit, scritta nel contratto. Il fee variabile si calcola SOLO sull'incrementale. Mai rev-share su tutta la revenue email per chi faceva già email: ti pagheresti il loro pregresso e al rinnovo se ne accorgono.

**Attribuzione:** revenue Klaviyo netta via skill *Klaviyo Revenue Attribution Audit* (esclusi ordini manuali, rimborsi, cancellati).

---

## 6. LE DUE REGOLE DI PRICING (valide per tutto)

1. **Floor — markup sul costo diretto: minimo 3,5×** (margine lordo ≥ 70%). Qualsiasi richiesta fuori listino si prezza così. Sotto il floor non si vende.
2. **Ceiling — ancora di valore:** il prezzo one-off deve restare sotto ~1 mese di revenue email incrementale stimata dall'audit. Finché vale, il prezzo si difende da solo.

**Principio lingue:** il costo marginale per lingua è ~zero (Canva translate) ma il prezzo segue il VALORE — un brand in 5 lingue opera in 5 mercati. Il processo efficiente è il nostro margine, non lo sconto del cliente.

**Metrica di controllo:** su ogni progetto tracciare prezzo ÷ ore totali di delivery (AM incluso). Floor: 100–150€/ora effettiva. Se scende, il prodotto si sta de-standardizzando.

---

## 7. ROUTING DEI LEAD (triage a 3 corsie)

| Corsia | Criterio | Offerta | Processo |
|---|---|---|---|
| **A — In target** | 25k€+/mese, Shopify | Setup/Rebuild premium + Retainer | WhatsApp → call conoscitiva → discovery |
| **B — Fuori target monetizzabile** | 8–25k€/mese, Shopify, lista esistente | Email Foundation Setup 2.000€+ | Pipeline GHL "Setup One-Off", vendita asincrona |
| **C — Fake / troppo piccoli / no Shopify** | — | Nurture leggero o scarto | — |

Il classifier GPT dell'AI Sales Setter mappa: *in target* → A, *early* → B, *fake* → C.
**Follow-up corsia B:** check-in automatico GHL a 6 mesi dal setup → candidato retainer.

---

## 8. QA MULTILINGUA (checklist minima)

- Proofreader madrelingua su subject, preheader, CTA, headline (30–50€/lingua, già nel prezzo).
- Allineamento testi/grafiche post-Canva (AM) — monitorare le ore: è l'unico costo marginale reale.
- Check formati locali: valuta, date, registro (tu/Sie/vous).
- Post-setup a 2 settimane: confronto open/click rate per lingua sullo stesso flusso. Una lingua >20–30% sotto le altre = traduzione da rivedere.

---

## 9. METRICHE DA TRACCIARE

- Conversione lead B → setup venduto
- €/ora effettiva per progetto (floor 100–150€)
- Upgrade rate setup → retainer (a 6–12 mesi)
- Upgrade rate pacchetto grafica → audit/rebuild (trigger a 90 giorni)
- Per i rev-share: revenue incrementale vs baseline, mese per mese

---

## 10. GRAND SLAM OFFER & GARANZIA ROI 3x

*Livello strategico sopra il listino. Impacchetta le offerte §1–5 in modo che il "no" costi al cliente più del "sì". Base: Value Equation di Hormozi.*

**Value Equation** — ogni offerta forte spinge le 4 leve:
`Valore = (Dream Outcome × Probabilità percepita) ÷ (Tempo × Sforzo)`
Alza in alto (risultato + certezza), abbassa in basso (tempo + fatica).

### 10.1 La garanzia — ROI-based, MAI revenue-based

**Regola d'oro:** non garantire mai la media (35–40% del fatturato a 6 mesi). Garantire il **pavimento**, consegnare la media. E ancorare la garanzia al **ROI sulla fee**, non al fatturato — così si schiva del tutto la trappola *attribuito ≠ incrementale*.

> **"L'email attribuita ti rende almeno 3× quello che mi paghi nei primi 90 giorni,
> o lavoro gratis finché non ci arriva. Primo flusso che genera cassa live entro 14 giorni."**

Perché regge da ogni angolo: fee €2.000 → servono €6.000 attribuiti = layup (la traiettoria reale è 5–8×). Anche se l'attribuzione gonfia del 30%, il canale vale comunque multipli della fee. Il cliente guarda il *suo* dashboard Klaviyo: numero indiscutibile, condiviso.

**Paletto anti-esposizione (qualificazione):** la garanzia 3× a 90 giorni regge solo se lo store è abbastanza grande. A 90 giorni l'email è in rampa (~15–20% del fatturato, non ancora 35%). €6.000 ÷ ~18% ≈ **store da €30k+/mese minimo.** Sotto quella soglia, la matematica non arriva al 3× → **non prendere il cliente** (coerente con la corsia A, §7). Il paletto protegge la garanzia *e* qualifica i lead: brand con lista + volume ordini = materia prima per l'email.

### 10.2 Architettura a due tracce

| | **Da zero** (no email attiva) | **Strutturato** (già-attivo) |
|---|---|---|
| **Chi** | DTC €30k+/mese, lista non monetizzata | DTC €50k+/mese, email attiva ma sotto-sfruttata |
| **Porta d'ingresso** | Build sprint €2.500 (setup + mese 1 incluso) | Audit + ottimizzazione €2.500 (+ mese 1 incluso) |
| **Dal mese 2** | €1.000 base + **15% del TOTALE attribuito** | €1.000 base + **15% del LIFT sopra baseline** |
| **Garanzia** | 0 → 30%+ del fatturato / 3× ROI in 90gg | +punti% sopra baseline / 3× ROI sul lift in 90gg |
| **Rev-share su** | Tutto l'attribuito (l'ha creato Mailift dal nulla) | Solo l'incrementale sopra baseline congelata (§5) |

**Nota "primo mese incluso":** in vendita è **incluso**, mai gratis (se lo ancori a zero, il €1.000/mese poi sembra caro). Bundlare il mese 1 nei €2.500 abbassa la cassa a 30gg ma dà un numero d'ingresso più pulito → meglio per la conversione finché mancano case study. **Quando avrai 5–6 clienti + case study forti: scorpora** (setup/audit €2.500 + mese 1 €1.000 a parte) → la cassa a 30gg raddoppia (vedi §11).

### 10.3 Seeds of doubt — l'onestà come arma di chiusura

In fase di vendita, pianta il seme del dubbio sui concorrenti: *"Ti diranno che ti portano il 35% di fatturato in più — è falso, quello è revenue attribuito, un KPI di canale, non soldi dal cielo; una parte di quei clienti comprava lo stesso. Io ti dico la verità e te la misuro giusta. Non ti fatturo il baseline che fai già — pago… anzi mi paghi solo il lift."* Dai al cliente una variabile di giudizio che non è il prezzo: sei l'unico che non gli mente e non gli ruba il credito. In un mercato di numeri gonfiati, **l'onestà misurata è il moat.**

---

## 11. UNIT ECONOMICS & MONEY MODEL

*La macchina che rende l'acquisizione auto-finanziata. Base: $100M Money Models (3 stadi: Get Cash → Get More Cash → Get The Most Cash).*

### 11.1 I numeri per cliente (baseline luglio 2026)

| Voce | Valore |
|---|---|
| Costo delivery / cliente / mese | **~€500** (€350 AM-copywriter + ~€150 grafiche, ~8 × €20) |
| CAC (ads) | **~€700** / cliente chiuso (referral ≈ €0) |
| Front-end (setup/audit) | **€2.500** upfront |
| Base retainer | €1.000 / mese |
| Rev-share | 15% (totale attribuito da zero / lift per strutturati) |

**Il costo di delivery è FISSO per cliente** (l'AM/copy costa €350 che il cliente paghi €1.000 o €3.000). Quindi **ogni euro di rev-share cade quasi puro a margine** — costo marginale ~0. È il motivo per cui il modello base+rev-share batte il flat: costi fissi, ricavi che scalano con la crescita del cliente, senza assumere.

### 11.2 Prima / dopo — perché il collo di bottiglia era la retention, non il CAC

| | Modello vecchio (flat €1.5k, retention 2 mesi) | Modello nuovo (base+rev-share, retention 6 mesi via garanzia) |
|---|---|---|
| CM / mese | €1.000 (66%) | ~€2.000 (80%) |
| Retention | 2 mesi | 6 mesi (garanzia 3×) |
| LTV | €2.000 | ~€12.000 |
| LTV : CAC | 2,9 : 1 | **~17 : 1** |

Stesso cliente, stesso CAC. Cambiano solo offerta + retention. **Il vincolo non è mai stato il CAC** — era il secchio bucato (retention) e il prezzo lasciato sul tavolo (no rev-share).

### 11.3 Acquisizione finanziata dal cliente (il colpo del money model)

**Front-end €2.500 > CAC €700.** Il cliente ti paga più per entrare di quanto costa acquisirlo → fai profitto il giorno che chiudi, *prima* del primo retainer. Ogni cliente si ripaga da solo e finanzia il prossimo → **puoi spingere le ads all'infinito.**

**Cassa a 30 giorni:**
- Incassi mese 1: front-end €2.500 (mese 1 incluso)
- Costi mese 1: CAC €700 + delivery €500 + consegna setup ~€400 = €1.600
- **Cassa netta ~€900** → CAC già recuperato + profitto

**Leva di scale:** Hormozi rule = cassa a 30gg ≥ **2× CAC**. Oggi ~1,3×. Come arrivarci → **scorpora / alza il front-end** (setup/audit €2.500 separato dal mese 1, o €3.000+). A quel punto ogni euro in ads torna raddoppiato nel primo mese → rubinetto aperto senza paura.

### 11.4 Le 4 leve della macchina (checklist)

1. **Offerta** con garanzia 3× ROI → firmano
2. **Retention** 6 mesi con la stessa garanzia → smettono di scappare (§10.1)
3. **Prezzo** base + rev-share → margine che scala senza costi (§11.1)
4. **Front-end > CAC** → acquisizione auto-finanziata → scale ads (§11.3)

**Core Four (lead):** solo dopo che 1–2 sono a posto. Non aggiungere un terzo canale — raddoppia quello che già converte (a questo stadio: referral). Fai *più* del provato prima di inventare il nuovo.
