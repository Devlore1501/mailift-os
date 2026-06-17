# Call: Review interno clienti e ottimizzazione processi Mailift

**Data:** 2026-04-27
**Partecipanti:** Lorenzo, Laura, Antonio
**Fonte:** Fathom AI Summary

## Riassunto esecutivo
Review strategico su tre clienti core con focus su ottimizzazione Klaviyo, segmentazione audience e workflow. Emergono inefficienze operative (materiali sparsi, flussi duplicati) e opportunità di revenue (upsell 3M, scaling winback IT per Kalishoes). Deciso di implementare Notion come hub centralizzato e potenziare autonomia di Laura e Antonio con call editoriali ricorrenti.

## Decisioni prese
- Adottare **Notion come source of truth** per materiali clienti e documentazione
- Centralizzare link drive in Notion per evitare frammentazione
- Istituire **call editoriali ricorrenti** con clienti (3M bisettimanale; altri cadenza da definire)
- Valutare **n8n** per automazioni workflow (Lorenzo mantiene Make Cloud in parallelo)
- Aumentare autonomia di Laura e Antonio con ownership su specifici clienti

## Action items
### Lorenzo / Mailift
- [ ] Setup Notion workspace come source of truth e migrare naming strutturato
- [ ] Mappare frequenze call editoriali per tutti i clienti (3M: bisettimanale confermato)
- [ ] Valutare onboarding n8n vs continuare con Make Cloud; fare POC se conveniente
- [ ] Delegare ownership cliente a Laura/Antonio con clear boundaries

### Cliente (Kalishoes)
- [ ] Implementare ottimizzazione popup (target: >1% conversion)
- [ ] Consolidare flussi Klaviyo: unificare welcome + post-purchase, riorganizzare per paese/lingua
- [ ] Disabilitare lead ads bassa qualità; scalare winback IT (baseline: €160 su 8 invii feb-apr)

### Cliente (Partilandia)
- [ ] Verificare logica checkout: rimuovere "confermato" pre-pagamento; usare "pagamento pending" come stop condition
- [ ] Creare journey separati: Gonfiabili (consultativo/authority) vs Palloncini (transazionale B2B)
- [ ] Redesign template: istituzionale, text-forward, social proof/partner focus (meno promo)

### Cliente (Treemme - 3M)
- [ ] Completare ~10 grafiche rimanenti package 20 email
- [ ] Preparare proposta upsell gestione mensile (timing: prossime 2-3 settimane)
- [ ] Confermare call editoriali bisettimanali in calendario

## Contesto aggiornato cliente

**Kalishoes:**
- Lead ads quality bassa (~4/19 buoni); Klaviyo sottoutilizzato (flussi frammentati, attribution window ristretta)
- Popup 1% conversion; traffico EN debole (180 visite/settimana)
- Winback IT: €160 potenziale da 8 invii (feb-apr) — scalabile se risorse allocate

**Partilandia (B2B):**
- Checkout custom causa "confermato pre-pagamento" → blocca automazioni standard
- Audience eterogenea (palloncini + gonfiabili; PMI + agenzie) richiede segmentazione sofisticata
- Costo integrazione Klaviyo: €700 (vendor custom WordPress)

**Treemme (3M):**
- 50% package completato; opportunità upsell imminente

## Segnali importanti
- **Opportunità revenue:** Winback IT Kalishoes ha ROI positivo a scala limitata (€160/8 invii) — test di scaling consigliato; Treemme upsell gestione mensile imminente
- **Rischio operativo:** Materiali sparsi + naming inconsistente ralenta onboarding Laura/Antonio; Notion mitiga ma richiede disciplina
- **Vincolo tecnico:** Partilandia checkout custom (€700) crea complessità Klaviyo; design journey separati è workaround necessario
- **Efficienza team:** Lorenzo intende delegare ma serve clarity; call editoriali ricorrenti formalizzano touchpoint cliente

## Note operative
- **Kalishoes:** Popup ottimizzazione è quick win (conversion 1%→target?); prioritizzare consolidamento flussi welcome/post-purchase per attribution corretta
- **Partilandia:** "Pagamento pending" come stop condition è pattern standard per checkpoint pre-pagamento; design più istituzionale richiede brief creativo chiaro (social proof, partner case studies, tono consultativo)
- **Treemme:** Call bisettimanali già impostate; monitorare % completion package e timing upsell (proposta quando ~70% completato)
- **Tech stack:** Notion + Make Cloud confermati core; n8n in valutazione (Lorenzo decider finale); n8n potrebbe consolidare se workflow complexity cresce

---