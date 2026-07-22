# API Contract v2 — autofatture-webapp

Base URL dev: `http://localhost:8000`
Tutti gli endpoint sono prefissati `/api`. CORS allow-list: `http://localhost:5173`.
Content-type JSON salvo `/statements/upload` (multipart) e i download PDF (`application/pdf`).

Breaking changes rispetto a v1:
- `AutofatturaLinePayload.vat_rate` rimosso. Nuovi campi: `vat_id`, `vat_rate_percent`.
- `AutofatturaPayload` ha nuovi campi: `supplier_country_iso`, `is_extra_ue`, `billing_data_warning`, `warning_message`, `verify_status`, `verified_data`.
- `PreviewResponse` ora include `skipped_italian: SkippedItalianItem[]` (trasparenza: fornitori IT esclusi dall'autofattura).
- `HealthResponse` include `db_ok`, `gmail_tokens_ok`, `anthropic_api_ok`.
- Job `kind` e `statement_id` esposti.

---

## Flusso atteso per una nuova run

```
1. POST /api/statements/upload (multipart)                  -> { statement_id }
2. POST /api/statements/{id}/parse                          -> transactions + outflows_count
3. POST /api/statements/{id}/classify  (async)              -> { job_id }
4. Poll GET /api/jobs/{job_id} finche' status="done"
5. POST /api/statements/{id}/verify-suppliers  (async)      -> { job_id }
6. Poll GET /api/jobs/{job_id}
7. GET  /api/statements/{id}/verify-suppliers/results       -> VerifyResultsResponse
8. POST /api/statements/{id}/preview                        -> PreviewResponse (autofatture + skipped_italian)
   (il preview applica automaticamente override e verify_results)
9. Utente edita/esclude righe in Review
10. POST /api/autofatture/create  { autofatture, dry_run, statement_id } -> { job_id }
11. Poll GET /api/jobs/{job_id} finche' status="done"
12. GET /api/history per vedere il run appena salvato
```

---

## System

### `GET /api/health`
```json
{
  "status": "ok",
  "fic_token_valid": true,
  "company": {"id": "1484061", "name": "Mailift Srl"},
  "detail": null,
  "dry_run": false,
  "db_ok": true,
  "gmail_tokens_ok": {"personal": true, "business": true},
  "anthropic_api_ok": true
}
```

### `GET /api/config`
```json
{
  "company_id": "1484061",
  "company_name": null,
  "numeration": "a",
  "payment_method": "MP05",
  "payment_account_hint": "Revolut",
  "dry_run": false,
  "blacklist_count": 3
}
```

---

## Statements

### `POST /api/statements/upload`  *(multipart/form-data)*
Field `file` — CSV/XLS/XLSX/PDF.
```json
{ "statement_id": "c2c730167e8d", "filename": "statement.csv", "size_bytes": 14728 }
```

### `POST /api/statements/{id}/parse`  *(sync)*
```json
{
  "statement_id": "c2c730167e8d",
  "transactions": [
    {"date": "2026-02-15", "amount": -42.00, "currency": "EUR", "description": "Google Ireland", "raw": "..."}
  ],
  "outflows_count": 60
}
```

### `POST /api/statements/{id}/classify`  *(async)*
```json
{ "job_id": "a1b2c3d4e5f6" }
```
Job result quando `status=done`:
```json
{
  "candidates_count": 14,
  "autofatture_count": 9,
  "autofatture": [/* AutofatturaPayload[] */],
  "skipped_italian": [/* SkippedItalianItem[] */],
  "skipped_count": 2
}
```

### `POST /api/statements/{id}/preview`  *(sync)*
```json
{
  "statement_id": "c2c730167e8d",
  "autofatture": [
    {
      "id": "af1",
      "type_doc": "TD17",
      "supplier_name": "Lovable Labs AB",
      "supplier_country": "SE",
      "supplier_country_iso": "SE",
      "supplier_vat_number": "SE559XXXXXXX01",
      "invoice_date": "2026-02-28",
      "period_label": "Febbraio 2026",
      "currency": "EUR",
      "ref_invoice_number": "",
      "ref_invoice_date": null,
      "excluded": false,
      "is_extra_ue": false,
      "billing_data_warning": false,
      "warning_message": "",
      "verify_status": "verified",
      "verified_data": {"supplier_vat_number": "SE559...", "bill_to_name": "Mailift Srl"},
      "lines": [
        {"description": "Lovable abbonamento", "amount_net": 20.00, "vat_id": 0, "vat_rate_percent": 22.0}
      ]
    },
    {
      "id": "af2",
      "type_doc": "TD17",
      "supplier_name": "OpenAI L.L.C.",
      "supplier_country": "US",
      "supplier_country_iso": "US",
      "supplier_vat_number": "",
      "invoice_date": "2026-02-28",
      "period_label": "Febbraio 2026",
      "currency": "EUR",
      "ref_invoice_number": "",
      "ref_invoice_date": null,
      "excluded": false,
      "is_extra_ue": true,
      "billing_data_warning": false,
      "warning_message": "",
      "verify_status": "pending",
      "verified_data": null,
      "lines": [
        {"description": "ChatGPT Plus", "amount_net": 20.00, "vat_id": 10, "vat_rate_percent": 0.0}
      ]
    }
  ],
  "skipped_italian": [
    {
      "supplier_name": "Google Cloud Italy Srl",
      "description": "Google Cloud billing",
      "amount": -35.50,
      "reason": "Google Cloud Italy Srl - IT, IVA 22% diretta",
      "source_transaction": {"date": "2026-02-10", "amount": -35.50, "description": "Google Cloud Italy"}
    }
  ]
}
```

Regole `vat_id`:
- UE (IT/IE/DE/FR/ES/NL/LT/SE/...) → `vat_id=0`, `vat_rate_percent=22.0`, `is_extra_ue=false` (reverse charge art.17 c.2)
- Extra-UE (US/GB/CH/CA/...) → `vat_id=10`, `vat_rate_percent=0.0`, `is_extra_ue=true` (non soggetta art.7-ter)

---

## Verify Suppliers

### `POST /api/statements/{id}/verify-suppliers`  *(async)*
```json
{ "job_id": "..." }
```
Progress nel job: `step_name="[3/16] OpenAI"`, `current`, `total`.

### `GET /api/statements/{id}/verify-suppliers/results`
```json
{
  "statement_id": "c2c730167e8d",
  "results": [
    {
      "supplier_key": "lovable",
      "supplier_name": "Lovable Labs AB",
      "status": "verified",
      "pdf_count": 1,
      "pdfs": ["lovable/invoice_2026_02.pdf"],
      "extracted": {
        "supplier_country": "SE",
        "supplier_vat_number": "SE559XXXXXXX01",
        "bill_to_name": "Mailift Srl",
        "total_net": 20.0,
        "vat_applied": false
      },
      "warning": null,
      "error": null
    },
    {
      "supplier_key": "gamma",
      "supplier_name": "Gamma Tech",
      "status": "bill_to_mismatch",
      "pdf_count": 0,
      "pdfs": [],
      "extracted": null,
      "warning": "Nessun PDF con bill to Mailift. Fatture trovate ma intestate a nominativo personale...",
      "error": null
    }
  ]
}
```

Status: `pending | verified | not_found | bill_to_mismatch | skipped`.

### `GET /api/suppliers/verify-rejects`
```json
[{"supplier_key": "gamma", "filename": "gamma_invoice_jan.pdf", "path": "gamma/gamma_invoice_jan.pdf", "size_bytes": 48123}]
```

### `GET /api/suppliers/verify-rejects/{relpath}`
Restituisce lo stream del PDF (`application/pdf`). `relpath` è il `path` del listing.

### `GET /api/suppliers/invoices/{supplier_key}`
```json
{ "supplier_key": "lovable", "files": ["invoice_2026_02.pdf"] }
```

### `GET /api/suppliers/invoices/{supplier_key}/{filename}`
Stream PDF scaricato.

---

## Supplier Overrides

### `GET /api/suppliers/overrides`
```json
[{"id": 1, "supplier_key": "higgsfield", "supplier_name_display": "Higgsfield", "country_iso": "US", "vat_number": "", "vat_id": 10, "note": "Default US", "updated_at": "2026-04-09T06:26:15.514556"}]
```

### `POST /api/suppliers/overrides`
Request:
```json
{"supplier_key": "Higgsfield Inc", "supplier_name_display": "Higgsfield", "country_iso": "US", "vat_number": "", "vat_id": 10, "note": "Default US"}
```
`supplier_key` viene normalizzato server-side (lowercase + strip suffix societari). Upsert per key.
Response: come `GET /api/suppliers/overrides` ma singolo oggetto.

### `DELETE /api/suppliers/overrides/{id}`
```json
{ "deleted": true }
```

---

## Autofatture create

### `POST /api/autofatture/create`  *(async)*
Request:
```json
{
  "autofatture": [/* AutofatturaPayload[] */],
  "dry_run": false,
  "statement_id": "c2c730167e8d"
}
```
Response: `{ "job_id": "..." }`.

Job result quando `status=done`:
```json
{
  "dry_run": false,
  "items": [
    {"status": "ok", "supplier": "Lovable Labs AB", "type_doc": "TD17", "total_net": 20.0, "fic_id": 123456, "fic_number": "12", "fic_numeration": "a", "fic_url": "https://secure.fattureincloud.it/issued-documents-edit/123456", "error": null}
  ],
  "ok": 1,
  "errors": 0,
  "skipped": 0
}
```
Una `RunHistory` row viene scritta automaticamente a fine job.

---

## Jobs

### `GET /api/jobs/{job_id}`
```json
{
  "id": "a1b2c3d4e5f6",
  "kind": "classify",
  "status": "running",
  "progress": 40,
  "step_name": "[3/16] OpenAI",
  "total": 16,
  "current": 3,
  "result": null,
  "error": null,
  "created_at": 1712658975.123,
  "statement_id": "c2c730167e8d"
}
```
`kind`: `classify | verify | create | generic`.
`status`: `pending | running | done | error`.

---

## History

### `GET /api/history`
```json
[
  {"id": 1, "statement_id": "c2c730167e8d", "started_at": "2026-04-09T06:30:01", "finished_at": "2026-04-09T06:32:14", "dry_run": false, "total_count": 9, "created_count": 9, "error_count": 0, "skipped_count": 0}
]
```

### `GET /api/history/{run_id}`
Come sopra + `result_json: CreatedItem[]`.

---

## TypeScript types (da copia-incollare in `webapp/frontend/src/types/api.ts`)

```ts
// -------------------- System
export type HealthStatus = "ok" | "error";
export interface HealthResponse {
  status: HealthStatus;
  fic_token_valid: boolean;
  company: { id: string; name?: string | null } | null;
  detail: string | null;
  dry_run: boolean;
  db_ok: boolean;
  gmail_tokens_ok: { personal: boolean; business: boolean };
  anthropic_api_ok: boolean;
}

export interface ConfigResponse {
  company_id: string;
  company_name: string | null;
  numeration: string;
  payment_method: string;
  payment_account_hint: string;
  dry_run: boolean;
  blacklist_count: number;
}

// -------------------- Statements
export interface UploadResponse {
  statement_id: string;
  filename: string;
  size_bytes: number;
}

export interface Transaction {
  date: string;
  amount: number;
  currency: string;
  description: string;
  raw: string | null;
}

export interface ParseResponse {
  statement_id: string;
  transactions: Transaction[];
  outflows_count: number;
}

// -------------------- Autofatture
export type TypeDoc = "TD17" | "TD18" | "TD19";
export type VerifyStatus = "pending" | "verified" | "not_found" | "bill_to_mismatch" | "skipped";

export interface AutofatturaLinePayload {
  description: string;
  amount_net: number;
  vat_id: number;            // 0 = 22% reverse charge UE, 10 = 0% extra-UE non soggetta
  vat_rate_percent: number;  // 22.0 | 0.0
}

export interface AutofatturaPayload {
  id: string;
  type_doc: TypeDoc;
  supplier_name: string;
  supplier_country: string;
  supplier_country_iso: string;
  supplier_vat_number: string;
  invoice_date: string; // YYYY-MM-DD
  period_label: string;
  currency: string;
  ref_invoice_number: string;
  ref_invoice_date: string | null;
  excluded: boolean;
  is_extra_ue: boolean;
  billing_data_warning: boolean;
  warning_message: string;
  verify_status: VerifyStatus;
  verified_data: Record<string, unknown> | null;
  lines: AutofatturaLinePayload[];
}

export interface SkippedItalianItem {
  supplier_name: string;
  description: string;
  amount: number;
  reason: string;
  source_transaction: Record<string, unknown> | null;
}

export interface PreviewResponse {
  statement_id: string;
  autofatture: AutofatturaPayload[];
  skipped_italian: SkippedItalianItem[];
}

// -------------------- Jobs
export type JobStatus = "pending" | "running" | "done" | "error";
export type JobKind = "classify" | "verify" | "create" | "generic";

export interface JobInfo {
  id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  step_name: string;
  total: number;
  current: number;
  result: unknown | null;
  error: string | null;
  created_at: number;
  statement_id: string | null;
}
export interface JobStartResponse { job_id: string }

// -------------------- Verify
export interface VerifySupplierResult {
  supplier_key: string;
  supplier_name: string;
  status: VerifyStatus;
  pdf_count: number;
  pdfs: string[];
  extracted: Record<string, unknown> | null;
  warning: string | null;
  error: string | null;
}
export interface VerifyResultsResponse {
  statement_id: string;
  results: VerifySupplierResult[];
}

export interface VerifyRejectItem {
  supplier_key: string;
  filename: string;
  path: string;
  size_bytes: number;
}

// -------------------- Overrides
export interface SupplierOverridePayload {
  id: number;
  supplier_key: string;
  supplier_name_display: string;
  country_iso: string;
  vat_number: string;
  vat_id: number;
  note: string;
  updated_at: string;
}
export interface SupplierOverrideCreate {
  supplier_key: string;
  supplier_name_display?: string;
  country_iso?: string;
  vat_number?: string;
  vat_id?: number;
  note?: string;
}

// -------------------- Create + History
export interface CreateRequest {
  autofatture: AutofatturaPayload[];
  dry_run: boolean;
  statement_id?: string;
}

export interface CreatedItem {
  status: "ok" | "error" | "skipped";
  supplier: string;
  type_doc: string;
  total_net: number;
  fic_id: number | null;
  fic_number: string | null;
  fic_numeration: string | null;
  fic_url: string | null;
  error: string | null;
}

export interface RunHistoryItem {
  id: number;
  statement_id: string | null;
  started_at: string;
  finished_at: string | null;
  dry_run: boolean;
  total_count: number;
  created_count: number;
  error_count: number;
  skipped_count: number;
}
export interface RunHistoryDetail extends RunHistoryItem {
  result_json: CreatedItem[] | null;
}
```

---

## Note operative per il frontend

1. **vat_id è deciso dal backend**: il frontend deve SOLO mostrare `vat_id`/`vat_rate_percent`/`is_extra_ue` e non calcolarli. Se l'utente cambia manualmente `supplier_country_iso` in un'edit inline, rilancia `POST /preview` per ricomputare.
2. **Warning billing** (`billing_data_warning=true`): mostra tooltip con `warning_message`. Tipicamente casi Gamma/ElevenLabs.
3. **Skipped italian**: render in un box "N transazioni escluse" sotto la tabella Review, NON mescolarle con le autofatture vere.
4. **Verify job è opzionale ma raccomandato**: se `anthropic_api_ok=false` l'analyze viene skippato ma i PDF vengono comunque scaricati; i results avranno `extracted=null`. Se `gmail_tokens_ok.*=false` per entrambi gli account il job torna tutti `not_found`.
5. **PDF preview**: usa `GET /api/suppliers/invoices/{key}/{filename}` in un iframe dentro un Dialog shadcn. I `pdfs` in `VerifySupplierResult` sono path relativi tipo `"lovable/invoice.pdf"` — il primo segmento è la key, il resto è il filename.
6. **Job polling**: consiglio 750ms di interval con React Query e stop appena `status in ["done","error"]`.
7. **Create dry-run**: tutti gli items tornano `status="skipped"` per simulare l'output senza chiamare FiC. La `RunHistory` viene scritta lo stesso con `dry_run=true`.
