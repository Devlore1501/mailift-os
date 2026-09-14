# Lead on Demand OS

Sistema di gestione Pay per Lead: acquisizione, prequalifica telefonica, routing ai clienti, pacchetti prepagati con ledger dei crediti, consegna a GoHighLevel, portale cliente e sostituzioni. Primo verticale: fotovoltaico. Il PRD completo è in [docs/PRD.md](docs/PRD.md), le scelte tecniche in [docs/DECISIONS.md](docs/DECISIONS.md).

## Struttura

```
packages/core   logica di dominio pura (stati lead, ledger, dedupe, routing, qualifica, territori)
packages/db     schema Drizzle per Postgres, migrazioni, seed (driver pg oppure pglite senza server)
apps/api        API Fastify: auth JWT, RBAC, servizi, GHL, webhook, coda job con retry, analytics
apps/web        Next.js: area admin, schermata operatore, portale cliente
docs/           PRD e decisioni
```

## Avvio in locale

Requisiti: Node 22, pnpm 10, Postgres 16 (oppure nessun database, vedi sotto).

```bash
cp .env.example .env            # imposta DATABASE_URL, JWT_SECRET, PUBLIC_LEAD_API_KEY
pnpm install
pnpm db:migrate                 # crea le tabelle
pnpm db:seed -- --demo          # template fotovoltaico + cliente demo Rossi Impianti
pnpm dev:api                    # API su http://localhost:4000
pnpm dev:web                    # web su http://localhost:3000
```

Senza Postgres: `DATABASE_URL=pglite://./.data/lod` usa un Postgres embedded su file. Stessa migrazione, stesso codice.

Accessi del seed demo:

| Ruolo | Email | Password |
|---|---|---|
| Super Admin | admin@leadondemand.it | admin12345 |
| Manager | manager@leadondemand.it | manager12345 |
| Operatore | operatore@leadondemand.it | operator12345 |
| Cliente (portale) | portale@rossiimpianti.it | cliente12345 |

## Test

```bash
pnpm test        # core (20 test) + api (17 test end-to-end su pglite in memoria)
pnpm check       # typecheck di tutti i pacchetti
```

Il test `apps/api/test/flow.test.ts` percorre il flusso della Definition of Done (PRD sez. 57): form, duplicati, coda operatori, script, qualifica, routing, addebito credito, invio GHL, portale, webhook idempotente, replacement con ritorno del credito, cap giornaliero, esclusiva territoriale, blocco a saldo zero, rinnovo, retry GHL con alert.

## Ingresso lead

```
POST /leads
x-api-key: <PUBLIC_LEAD_API_KEY>
{
  "firstName": "Mario", "lastName": "Rossi", "phone": "340 123 4567", "email": "mario@example.com",
  "address": "Via Roma 1", "municipality": "Vicenza", "postalCode": "36100", "province": "VI", "region": "Veneto",
  "source": "meta", "campaignName": "PV Veneto settembre", "utmSource": "facebook", "attributedCost": 12.5,
  "consentRecorded": true,
  "answers": { "owner": "true", "monthly_bill": 180 }
}
```

Telefono ed email vengono normalizzati; con lo stesso telefono o email entro la finestra duplicati (default 90 giorni) il lead viene registrato come duplicato e non entra in pipeline. Il campo `answers` accetta risposte già raccolte dal form: l'operatore le vede compilate nello script.

## Flusso operativo

1. Il lead entra in `TO_CONTACT` e compare nella coda operatori.
2. L'operatore apre la schermata chiamata: dati a sinistra, script a salti condizionali al centro, risposte e score a destra, barra con Non risponde / Richiama / Qualificato / Non qualificato / Fissa appuntamento.
3. Su Qualificato il Routing Engine sceglie il cliente (verticale, tipologia, territorio, esclusiva, credito, cap, criteri del cliente) e, per l'offerta con prequalifica, consegna subito: `DELIVERY -1` nel ledger, stato `DELIVERED`, job di invio a GHL, evento `lead.delivered`.
4. Per l'offerta "lead + appuntamento" l'addebito avviene quando viene fissato l'appuntamento.
5. Se nessun cliente è disponibile il lead va in `WAITING_ASSIGNMENT` con i motivi; la coda si riprova dopo un rinnovo o un nuovo territorio.
6. Il cliente vede il lead nel portale, registra l'esito e può chiedere la sostituzione entro lo SLA. Se approvata: `REPLACEMENT +1` e lead marcato sostituito.
7. A saldo zero il pacchetto passa a `COMPLETED`, il routing verso quel pacchetto si blocca e parte la notifica di rinnovo.

## GoHighLevel

In uscita (job `ghl.deliver`, 5 tentativi con backoff): upsert contatto con tag `lead-on-demand`, `lod:<codice>`, `lod:<categoria>`, custom field secondo il mapping configurato, opportunità nella pipeline del cliente, nota con tutte le risposte. Credenziali: token globale `GHL_API_KEY` più Location ID dalla scheda cliente, oppure un token dedicato per cliente in Integrazioni.

In entrata (`POST /webhooks/ghl`, header `x-webhook-secret`): eventi `appointment.created|confirmed|rescheduled|cancelled|show|no_show`, `sale.won`, `sale.lost`, `opportunity.updated`, `contact.updated`. Ogni evento è idempotente su `event_id` (o hash del payload). I lead vengono riconosciuti da `contact_id`, `lead_code` o `opportunity.id`.

Eventi in uscita verso il webhook del cliente (firma HMAC SHA-256 in `X-LOD-Signature`): `lead.created`, `lead.qualified`, `lead.assigned`, `lead.delivered`, `lead.rejected`, `lead.replacement_requested`, `lead.replaced`, `package.low_balance`, `package.completed`, `appointment.booked`, `appointment.show`, `appointment.no_show`, `sale.won`, `sale.lost`.

## Ruoli

| | Super Admin | Manager | Operatore | Cliente |
|---|---|---|---|---|
| Lead, coda, qualifica | sì | sì | solo propri / in coda | solo consegnati a sé |
| Clienti, pacchetti, territori, routing | sì | sì | no | no |
| Replacement: decidere | sì | sì | no | richiedere |
| Economics, campagne, rettifiche ledger, team, token GHL | sì | no | no | no |

Il portale cliente ricava il tenant dal token JWT: nessun parametro dell'URL o del body può cambiare il cliente interrogato.

## Deploy

API: qualsiasi host Node 22 con Postgres raggiungibile (`pnpm --filter @lod/api start`, le migrazioni girano all'avvio). Web: Vercel o Node (`next build`, `NEXT_PUBLIC_API_URL` verso l'API). Il worker dei job gira dentro il processo API; per più istanze API il lock ottimistico sulla tabella `jobs` evita doppie esecuzioni.
