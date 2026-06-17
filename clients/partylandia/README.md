# Partylandia

**Contatto principale:** Barbara Turcatel (owner)
**Team cliente:** Roberto (dev/tech lead)
**Email:** info@partylandia.com
**Sito:** partylandia.com (IT) + prim-globos.es (ES)
**Stack:** Custom backend (WordPress-like) + Klaviyo (migrazione da Brevo)
**Stato:** One-shot — onboarding mar 2026
**MRR attuale:** —

## Contesto business
eCommerce B2B/B2C palloncini e gonfiabili. Due audience principali: privati (palloncini) e agenzie/intermediari (gonfiabili). Sito custom con backend proprietario gestito da Roberto. Checkout con bonifico (ordine "sospeso" fino a pagamento). Sito spagnolo Prim Globos con quasi zero conversioni. Server-side pixel Facebook già attivo.

## Ultime decisioni
_Ultima call: [2026-04-08](calls/2026-04-08_analisi-copy-e-offerte-popup-partylandia.md)_

- **Offerta Palloncini:** +100 palloncini personalizzati omaggio su ordini >500€ (da erogare via codice promo o processo manuale)
- **Offerta Gonfiabili:** compressore elettrico gratuito (costo ~25€, retail ~70€)
- **Percorso Agenzie:** Partner Program con benefici scalabili (attivazione da 10+ ordini/anno)
- **Prossimo passo:** Bozze copy per 3 popup + connessione con designer per catalogo agenzie


## Prossimi step
### Lorenzo / Mailift
- [ ] Contattare Roberto per fix tracking analytics
- [ ] Redigere 3 bozze copy per popup (Palloncini, Gonfiabili, Agenzie)
- [ ] Connettere prospect con designer per sviluppo catalogo agenzie

### Cliente
- [ ] Risolvere situazione logistica gazebo in dogana
- [ ] Confermare preferenza formato promozione Palloncini (codice promo vs. manuale)
- [ ] Validare bozze copy


## Note operative
- Checkout bonifico: non triggera eventi standard Shopify — Roberto deve emettere evento "bonifico paid" per chiudere flussi abandon
- GDPR: preferenza server-side per script; consenso popup obbligatorio
- Sito ES: probabile problema traduzione + prezzi; non prioritario ora
