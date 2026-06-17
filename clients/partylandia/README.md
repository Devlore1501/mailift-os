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
_Ultima call: [2026-03-25](calls/2026-03-25_review-pre-kickoff-partylandia---email-marketing-s.md)_

- Avvio ottimizzazione checkout (riduzione friction, pre-compilazione campi, popup lead capture)
- Implementazione automazioni email: welcome series, abandoned cart recovery, campagne segmentate
- Accesso Lorenzo agli account advertising e piattaforme per audit dettagliato
- Timeline setup: 72 ore da kickoff
- Esplorazione canali alternativi: TikTok, Facebook/Google Ads ottimizzate


## Prossimi step
### Lorenzo / Mailift
- [ ] Richiedere e documentare accesso ai sistemi (Google Ads, e-commerce, email platform, social ads)
- [ ] Preparare audit dettagliato dei costi e performance Google Ads
- [ ] Delineare roadmap TikTok e social paid (briefing pre-kickoff)
- [ ] Schedulare call follow-up settimanale
- [ ] Confermare setup 72 ore con checklist pre-30 marzo

### Cliente (Partylandia)
- [ ] Fornire credenziali accesso account advertising e CRM/email
- [ ] Condividere histórico dati clienti (4.000+ database)
- [ ] Confirmación partecipazione kickoff 30 marzo


## Note operative
- Checkout bonifico: non triggera eventi standard Shopify — Roberto deve emettere evento "bonifico paid" per chiudere flussi abandon
- GDPR: preferenza server-side per script; consenso popup obbligatorio
- Sito ES: probabile problema traduzione + prezzi; non prioritario ora
