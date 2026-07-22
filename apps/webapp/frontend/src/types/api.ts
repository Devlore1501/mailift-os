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
export type VerifyStatus =
  | "pending"
  | "verified"
  | "pdf_only"
  | "not_found"
  | "bill_to_mismatch"
  | "skipped";

export interface AutofatturaLinePayload {
  description: string;
  amount_net: number;
  vat_id: number;
  vat_rate_percent: number;
}

export interface AutofatturaPayload {
  id: string;
  type_doc: TypeDoc;
  supplier_name: string;
  supplier_key: string;
  supplier_country: string;
  supplier_country_iso: string;
  supplier_vat_number: string;
  invoice_date: string;
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
export interface JobStartResponse {
  job_id: string;
}

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

export interface CreateJobResult {
  dry_run: boolean;
  items: CreatedItem[];
  ok: number;
  errors: number;
  skipped: number;
}

export interface ClassifyJobResult {
  candidates_count: number;
  autofatture_count: number;
  autofatture: AutofatturaPayload[];
  skipped_italian: SkippedItalianItem[];
  skipped_count: number;
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
