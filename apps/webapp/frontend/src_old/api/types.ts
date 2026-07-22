export type Health = {
  status: "ok" | "error";
  fic_token_valid: boolean;
  company?: { id: string; name?: string };
  detail?: string;
  dry_run: boolean;
};

export type Config = {
  company_id: string;
  company_name?: string | null;
  numeration: string;
  payment_method: string;
  payment_account_hint: string;
  dry_run: boolean;
};

export type UploadResponse = {
  statement_id: string;
  filename: string;
  size_bytes: number;
};

export type Transaction = {
  date: string;
  amount: number;
  currency: string;
  description: string;
  raw?: string;
};

export type ParseResponse = {
  statement_id: string;
  transactions: Transaction[];
  outflows_count: number;
};

export type AutofatturaLine = {
  description: string;
  amount_net: number;
  vat_rate: number;
};

export type Autofattura = {
  id: string;
  type_doc: "TD17" | "TD18" | "TD19";
  supplier_name: string;
  supplier_country: string;
  supplier_vat_number: string;
  invoice_date: string;
  period_label: string;
  currency: string;
  ref_invoice_number: string;
  ref_invoice_date: string | null;
  excluded: boolean;
  lines: AutofatturaLine[];
};

export type JobInfo = {
  id: string;
  status: "pending" | "running" | "done" | "error";
  progress: number;
  step_name: string;
  total: number;
  current: number;
  result: any;
  error: string | null;
  created_at: number;
};

export type CreatedItem = {
  status: "ok" | "error" | "skipped";
  supplier: string;
  type_doc: string;
  total_net: number;
  fic_id?: number | null;
  fic_number?: string | null;
  fic_numeration?: string | null;
  fic_url?: string | null;
  error?: string | null;
};

export type CreateResult = {
  dry_run: boolean;
  items: CreatedItem[];
  ok: number;
  errors: number;
  skipped: number;
};
