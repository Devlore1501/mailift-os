// Tipi TS per il contratto API di Mailift Planner (planner/design/api_contract.md).

// -------------------- System

export interface SystemStatus {
  ok: boolean;
  version: string;
  anthropic_configured: boolean;
  notion_configured: boolean;
  mock_mode: boolean;
}

// -------------------- Brands

export interface BrandAvatar {
  who: string;
  desires: string[];
  objections: string[];
  language: string;
  notes: string;
}

export interface Brand {
  id: number;
  name: string;
  description: string;
  tone_of_voice: string;
  mission: string;
  positioning: string;
  avatar: BrandAvatar;
  emails_per_week: number;
  country: string;
  klaviyo_configured: boolean;
  created_at: string;
  updated_at: string;
}

export type PlanStatus =
  | "generating"
  | "draft"
  | "approved"
  | "published"
  | "error";

export interface BrandSummary {
  id: number;
  name: string;
  positioning: string;
  emails_per_week: number;
  klaviyo_configured: boolean;
  num_products: number;
  num_active_offers: number;
  last_plan_status: PlanStatus | null;
  last_plan_month_start: string | null;
  created_at: string;
}

export interface BrandCreate {
  name: string;
  description?: string;
  tone_of_voice?: string;
  mission?: string;
  positioning?: string;
  avatar?: Partial<BrandAvatar>;
  emails_per_week?: number;
  country?: string;
}

export type BrandUpdate = Partial<Omit<Brand, "id" | "created_at" | "updated_at" | "klaviyo_configured">>;

// -------------------- Catalogo

export interface Product {
  id: number;
  brand_id: number;
  name: string;
  category: string;
  price: number | null;
  seasonality: string;
  is_best_seller: boolean;
  url: string;
  notes: string;
}

export interface ProductInput {
  name: string;
  category?: string;
  price?: number | null;
  seasonality?: string;
  is_best_seller?: boolean;
  url?: string;
  notes?: string;
}

export interface Offer {
  id: number;
  brand_id: number;
  name: string;
  code: string;
  discount: string;
  valid_from: string | null;
  valid_to: string | null;
  active: boolean;
  notes: string;
}

export interface OfferInput {
  name: string;
  code?: string;
  discount?: string;
  valid_from?: string | null;
  valid_to?: string | null;
  active?: boolean;
  notes?: string;
}

export interface Occasion {
  id: number;
  brand_id: number;
  name: string;
  date: string | null;
  notes: string;
}

export interface OccasionInput {
  name: string;
  date?: string | null;
  notes?: string;
}

export type LaunchKind = "lancio" | "promo";

export interface Launch {
  id: number;
  brand_id: number;
  name: string;
  kind: LaunchKind;
  start_date: string;
  end_date: string;
  subject: string;
  notes: string;
  active: boolean;
}

export interface LaunchInput {
  name: string;
  kind?: LaunchKind;
  start_date?: string;
  end_date?: string;
  subject?: string;
  notes?: string;
  active?: boolean;
}

// -------------------- Klaviyo

export interface KlaviyoStatus {
  configured: boolean;
  key_preview: string | null;
  account_name: string | null;
  last_sync_at: string | null;
  error: string | null;
}

export interface KlaviyoSegment {
  klaviyo_id: string;
  name: string;
  profile_count: number | null;
}

export interface KlaviyoCampaign {
  klaviyo_id: string;
  name: string;
  sent_at: string | null;
  recipients: number | null;
  open_rate: number | null;
  click_rate: number | null;
  revenue: number | null;
}

export type EngagementHealth = "good" | "average" | "poor" | "unknown";

export interface KlaviyoMetricsSummary {
  avg_open_rate: number | null;
  avg_click_rate: number | null;
  total_revenue_30d: number | null;
  campaigns_last_30d: number;
  engagement_health: EngagementHealth;
}

export interface KlaviyoSnapshot {
  synced_at: string;
  account_name: string | null;
  total_profiles: number | null;
  segments: KlaviyoSegment[];
  campaigns: KlaviyoCampaign[];
  metrics_summary: KlaviyoMetricsSummary;
  recommendations: string[];
}

// -------------------- Notion settings

export interface NotionSettings {
  configured: boolean;
  token_preview: string | null;
  templates_db_id: string | null;
  calendar_parent_page_id: string | null;
  templates_synced: number;
  templates_last_sync_at: string | null;
}

export interface NotionSettingsUpdate {
  token?: string;
  templates_db_id?: string;
  calendar_parent_page_id?: string;
}

// -------------------- Template Canva

export interface Template {
  id: number;
  notion_page_id: string;
  name: string;
  category: string;
  canva_url: string;
  tags: string[];
  preview_url: string;
  notion_url: string;
}

export interface TemplateCategory {
  category: string;
  count: number;
}

export interface TemplatesSyncResult {
  synced: number;
  categories: number;
}

export interface CanvaSetEntry {
  name: string;
  count: number;
  category: string;
}

export interface CanvaSet {
  canva_file_url: string;
  entries: CanvaSetEntry[];
  template_count: number;
  categories: string[];
}

export interface CanvaSetIn {
  canva_file_url: string;
  entries?: CanvaSetEntry[];
  entries_text?: string;
}

export interface PreviewUploadResult {
  saved: number;
  matched: number;
}

// -------------------- Piani editoriali

export type EmailObjective = "nurturing" | "promo" | "storytelling" | "vendita";
export type EmailFormat = "grafica" | "testuale";

/** Blocco copy della scaletta per il designer (email grafiche). */
export interface EmailBlock {
  type: "banner" | "sezione" | "info" | "cta_finale" | string;
  headline: string;
  subheadline: string;
  text: string;
  cta: string;
  visual: string;
}
export type EmailStatus = "draft" | "edited" | "approved";

export interface PlanSummary {
  id: number;
  brand_id: number;
  month_start: string;
  status: PlanStatus;
  num_emails: number;
  notes: string | null;
  error: string | null;
  notion_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailSegment {
  name: string;
  klaviyo_segment_id: string | null;
  rationale: string;
}

export interface EmailProductRef {
  name: string;
  reason: string;
}

export interface EmailOfferRef {
  name: string;
  code: string;
  discount: string;
}

export type CampaignRole =
  | "teaser"
  | "annuncio"
  | "follow_up"
  | "last_call"
  | "final_reminder"
  | "altro";

/** Appartenenza dell'email a una sequenza lancio/promo. */
export interface EmailCampaignRef {
  name: string;
  role: CampaignRole | string;
}

/** Strategia di una sequenza lancio/promo a livello di piano. */
export interface PlanCampaign {
  name: string;
  kind: LaunchKind | string;
  strategy: string;
  proposals: string[];
}

export interface EmailCanvaTemplate {
  template_id: number | null;
  name: string;
  category: string;
  canva_url: string;
  preview_url?: string;
}

export interface PlanEmail {
  id: number;
  plan_id: number;
  position: number;
  send_date: string;
  send_day: string;
  send_time: string;
  objective: EmailObjective;
  format: EmailFormat;
  theme: string;
  angle: string;
  segment: EmailSegment | null;
  subject_variants: string[];
  preview_text: string;
  body: string;
  blocks: EmailBlock[];
  campaign: EmailCampaignRef | null;
  products: EmailProductRef[];
  offer: EmailOfferRef | null;
  canva_template: EmailCanvaTemplate | null;
  status: EmailStatus;
  updated_at: string;
}

export interface PlanDetail extends PlanSummary {
  emails: PlanEmail[];
  campaigns: PlanCampaign[];
  context_snapshot: Record<string, unknown>;
}

export interface PlanGenerateRequest {
  month_start: string;
  num_emails: number;
  notes?: string;
}

export interface PlanUpdate {
  status?: "approved" | "draft";
  notes?: string;
}

export interface PlanEmailUpdate {
  send_time?: string;
  subject_variants?: string[];
  preview_text?: string;
  body?: string;
  blocks?: EmailBlock[];
  format?: EmailFormat;
  segment?: EmailSegment;
  status?: EmailStatus;
}

export interface PlanPublishResult {
  status: "published";
  notion_database_id: string;
  notion_url: string;
  pages: { email_id: number; notion_url: string }[];
}

export interface ExtractedProduct {
  name: string;
  category: string;
  price: number | null;
  is_best_seller: boolean;
}

export interface ExtractedProfile {
  description: string;
  tone_of_voice: string;
  mission: string;
  positioning: string;
  avatar: BrandAvatar;
  products: ExtractedProduct[];
  extraction_notes: string;
  applied: boolean;
  products_created: number;
}

export interface OccasionSuggestion {
  name: string;
  date: string;
  kind: string; // festività | ponte | ricorrenza
  idea: string;
}

export interface OccasionSuggestOut {
  country: string;
  month: string;
  suggestions: OccasionSuggestion[];
}
