# MAILIFT — LISTINO & REGOLE DI PRICING
*Documento interno · v1.0 · Giugno 2026*

> Riferimento per preventivi. Tutti i prezzi derivano da due regole fisse (§5).
> Non scendere sotto i prezzi minimi senza ricalcolare il margine.

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
