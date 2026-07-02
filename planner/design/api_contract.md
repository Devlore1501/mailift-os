# Mailift Planner — API Contract v1

SaaS multi-cliente per generare piani editoriali email settimanali (Klaviyo + Claude + Notion/Canva).

- Backend: FastAPI su `http://localhost:8001`, tutte le route sotto `/api`.
- Frontend: Vite dev su `:5174` con proxy `/api` → `http://localhost:8001`.
- Multi-tenancy: ogni **brand** è un workspace isolato. Le risorse figlie sono scoped per brand.
- Tutte le date ISO `YYYY-MM-DD`, orari `HH:MM`, datetime ISO 8601 UTC.
- Errori: `{"detail": "messaggio"}` con status 4xx/5xx.

## System

### GET /api/system/status
```json
{
  "ok": true,
  "version": "0.1.0",
  "anthropic_configured": true,
  "notion_configured": false,
  "mock_mode": false
}
```
`mock_mode=true` quando manca `ANTHROPIC_API_KEY`: la generazione ritorna piani demo deterministici (l'app resta usabile end-to-end).

## Brands (workspace)

### Brand object
```json
{
  "id": 1,
  "name": "Bergamo Vini",
  "description": "Cantina DTC...",
  "tone_of_voice": "Prima persona, confidenziale, da enologo",
  "mission": "...",
  "positioning": "...",
  "avatar": {
    "who": "Appassionato di vino 35-60...",
    "desires": ["bere meglio", "scoprire cantine"],
    "objections": ["prezzo", "spedizione"],
    "language": "informale, evocativo",
    "notes": ""
  },
  "emails_per_week": 3,
  "klaviyo_configured": true,
  "created_at": "2026-07-01T10:00:00Z",
  "updated_at": "2026-07-01T10:00:00Z"
}
```

- `GET /api/brands` → `BrandSummary[]`: `{id, name, positioning, emails_per_week, klaviyo_configured, num_products, num_active_offers, last_plan_status, last_plan_week_start, created_at}`
- `POST /api/brands` — body: `{name}` (obbligatorio) + qualunque altro campo del Brand → Brand (201)
- `GET /api/brands/{brand_id}` → Brand
- `PATCH /api/brands/{brand_id}` — campi parziali → Brand
- `DELETE /api/brands/{brand_id}` → 204 (cancella tutto il workspace)

## Catalogo prodotti

### Product object
```json
{"id": 1, "brand_id": 1, "name": "Valcalepio Rosso DOC", "category": "Vini rossi",
 "price": 14.5, "seasonality": "autunno-inverno", "is_best_seller": true,
 "url": "https://...", "notes": ""}
```
- `GET /api/brands/{brand_id}/products` → `Product[]`
- `POST /api/brands/{brand_id}/products` — `{name}` obbligatorio → Product (201)
- `PATCH /api/products/{product_id}` → Product
- `DELETE /api/products/{product_id}` → 204

## Offerte / codici sconto

### Offer object
```json
{"id": 1, "brand_id": 1, "name": "Flash sale fine mese", "code": "GIUGNO20",
 "discount": "-20%", "valid_from": "2026-06-27", "valid_to": "2026-06-30",
 "active": true, "notes": ""}
```
- `GET /api/brands/{brand_id}/offers` → `Offer[]`
- `POST /api/brands/{brand_id}/offers` — `{name}` obbligatorio → Offer (201)
- `PATCH /api/offers/{offer_id}` → Offer
- `DELETE /api/offers/{offer_id}` → 204

## Occasioni / temi del periodo

### Occasion object
```json
{"id": 1, "brand_id": 1, "name": "Ferragosto", "date": "2026-08-15", "notes": "grigliate, vini freschi"}
```
- `GET /api/brands/{brand_id}/occasions` → `Occasion[]`
- `POST /api/brands/{brand_id}/occasions` — `{name}` obbligatorio → Occasion (201)
- `PATCH /api/occasions/{occasion_id}` → Occasion
- `DELETE /api/occasions/{occasion_id}` → 204

## Integrazione Klaviyo (per brand)

- `PUT /api/brands/{brand_id}/klaviyo` — body `{"api_key": "pk_..."}`. Salva la chiave (mai ritornata in chiaro). → `KlaviyoStatus`
- `DELETE /api/brands/{brand_id}/klaviyo` → 204 (scollega)
- `GET /api/brands/{brand_id}/klaviyo/status` → `KlaviyoStatus`
```json
{"configured": true, "key_preview": "pk_abc1...", "account_name": "Bergamo Vini",
 "last_sync_at": "2026-07-01T10:00:00Z", "error": null}
```
- `POST /api/brands/{brand_id}/klaviyo/sync` — legge segmenti/liste/campagne da Klaviyo e salva uno snapshot. → `KlaviyoSnapshot`. Se la chiave non è valida → 502 con detail.
- `GET /api/brands/{brand_id}/klaviyo/insights` → ultimo `KlaviyoSnapshot` salvato, oppure 404 se mai sincronizzato.

### KlaviyoSnapshot
```json
{
  "synced_at": "2026-07-01T10:00:00Z",
  "account_name": "Bergamo Vini",
  "total_profiles": 12400,
  "segments": [
    {"klaviyo_id": "Xy12ab", "name": "Engaged 30 days", "profile_count": 3200}
  ],
  "campaigns": [
    {"klaviyo_id": "01H...", "name": "Newsletter 24/06", "sent_at": "2026-06-24T07:30:00Z",
     "recipients": 3100, "open_rate": 0.41, "click_rate": 0.021, "revenue": 830.0}
  ],
  "metrics_summary": {
    "avg_open_rate": 0.38, "avg_click_rate": 0.018, "total_revenue_30d": 4200.0,
    "campaigns_last_30d": 8, "engagement_health": "good"
  },
  "recommendations": [
    "Open rate medio 38%: lista sana, ok frequenza attuale",
    "Segmento 'Unengaged 90d' con 4.1k profili: pianificare re-engagement"
  ]
}
```
`engagement_health`: `"good" | "average" | "poor" | "unknown"`.

## Impostazioni Notion (globali, livello agenzia)

- `GET /api/settings/notion` →
```json
{"configured": true, "token_preview": "ntn_a1...", "templates_db_id": "abc123",
 "calendar_parent_page_id": "def456", "templates_synced": 348,
 "templates_last_sync_at": "2026-07-01T09:00:00Z"}
```
- `PUT /api/settings/notion` — body parziale `{token?, templates_db_id?, calendar_parent_page_id?}` → come GET

## Template Canva (letti dal DB Notion)

### Template object
```json
{"id": 12, "notion_page_id": "b3c...", "name": "Promo Bold 04", "category": "promo",
 "canva_url": "https://www.canva.com/design/...", "tags": ["sconto", "urgenza"],
 "notion_url": "https://notion.so/..."}
```
Categorie note (aperte, non enum rigido): `promo`, `newsletter`, `lancio prodotto`, `storytelling`, `abbandono`, `benvenuto`, `re-engagement`, `stagionale`.

- `GET /api/templates?category=promo&q=bold` → `Template[]` (filtri opzionali)
- `GET /api/templates/categories` → `[{"category": "promo", "count": 62}, ...]`
- `POST /api/templates/sync` → legge il database Notion e aggiorna la cache locale → `{"synced": 348, "categories": 8}`. 502 se Notion non configurato/non raggiungibile (in mock_mode: seeda ~30 template demo).

## Piani editoriali

### Plan lifecycle
`generating` → `draft` → `approved` → `published` (oppure `error` se la generazione fallisce, con `error` valorizzato).

### PlanSummary
```json
{"id": 7, "brand_id": 1, "week_start": "2026-07-06", "status": "draft",
 "num_emails": 3, "notes": "focus estate", "error": null,
 "notion_url": null, "created_at": "...", "updated_at": "..."}
```

### PlanEmail object
```json
{
  "id": 31,
  "plan_id": 7,
  "position": 1,
  "send_date": "2026-07-07",
  "send_day": "martedì",
  "send_time": "09:30",
  "objective": "nurturing",
  "theme": "Storia della vendemmia in anticipo",
  "angle": "Dietro le quinte: perché quest'anno si vendemmia prima",
  "segment": {
    "name": "Engaged 30 days",
    "klaviyo_segment_id": "Xy12ab",
    "rationale": "Open rate alto sul segmento engaged; contenuto puro senza promo"
  },
  "subject_variants": ["Si vendemmia già?", "Quest'anno l'uva ha fretta", "Una vendemmia mai vista"],
  "preview_text": "Ti racconto cosa sta succedendo tra i filari",
  "body": "Ciao {{ first_name }},\n\n...",
  "products": [{"name": "Valcalepio Rosso DOC", "reason": "citato nel racconto"}],
  "offer": null,
  "canva_template": {"template_id": 12, "name": "Storytelling Vigna 02", "category": "storytelling",
                     "canva_url": "https://www.canva.com/design/..."},
  "status": "draft",
  "updated_at": "..."
}
```
- `objective`: `"nurturing" | "promo" | "storytelling" | "vendita"`.
- `offer`: `{"name": "...", "code": "GIUGNO20", "discount": "-20%"}` oppure `null`.
- `body`: testo email completo in markdown leggero (hook, corpo, CTA).
- `status` email: `"draft" | "edited" | "approved"`.

### Endpoints
- `GET /api/brands/{brand_id}/plans` → `PlanSummary[]` (desc per week_start)
- `POST /api/brands/{brand_id}/plans/generate` — body:
  `{"week_start": "2026-07-06", "num_emails": 3, "notes": "opzionale, indicazioni libere"}`
  → 202 `PlanSummary` con `status:"generating"`. La generazione gira in background (Claude); il frontend fa polling su GET plan ogni ~2s finché status ≠ `generating`.
  Se esiste già un piano per quella settimana → 409.
- `GET /api/plans/{plan_id}` → `{...PlanSummary, "emails": PlanEmail[], "context_snapshot": {...}}`
- `PATCH /api/plans/{plan_id}` — `{"status": "approved"}` (solo transizioni draft→approved, approved→draft) o `{"notes": "..."}` → PlanSummary
- `DELETE /api/plans/{plan_id}` → 204
- `PATCH /api/plans/{plan_id}/emails/{email_id}` — campi parziali (subject_variants, body, send_time, segment, status, ecc.). Un edit manuale porta `status:"edited"`. → PlanEmail
- `POST /api/plans/{plan_id}/emails/{email_id}/regenerate` — body `{"instructions": "più corto, più urgenza"}` (opzionale). **Sincrono** (10-40s): il frontend mostra spinner sulla card. → PlanEmail rigenerata
- `POST /api/plans/{plan_id}/publish` — pubblica il piano approvato su Notion come calendario editoriale (una pagina per email in un database Notion). Richiede `status:"approved"` (altrimenti 409) e Notion configurato (altrimenti 502; in mock_mode simula e ritorna URL finti). →
```json
{"status": "published", "notion_database_id": "...", "notion_url": "https://notion.so/...",
 "pages": [{"email_id": 31, "notion_url": "https://notion.so/..."}]}
```

## Note per il frontend

- Lingua UI: **italiano**.
- Brand switcher sempre visibile (topbar): dropdown/command con ricerca, ricorda l'ultimo brand in localStorage.
- Route: `/` dashboard agenzia (griglia brand) · `/brands/:brandId/plans` (default workspace) · `/brands/:brandId/plans/:planId` · `/brands/:brandId/profile` · `/brands/:brandId/catalog` · `/brands/:brandId/integrations` · `/templates` · `/settings`.
- La card email del piano mostra tutti gli 8 elementi: giorno+orario, tema/angolo+obiettivo (badge colorato), segmento con rationale, 2-3 oggetti A/B, preview text, corpo espandibile, prodotti/offerta, template Canva con link.
- Regola 80/20 visibile: nel piano un indicatore contenuto vs promo (conteggio obiettivi).
