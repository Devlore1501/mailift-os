// Shapes del contratto API backend.

export interface User {
  id: number;
  name: string;
  email: string;
  role: "admin" | "editor" | "contributor";
  active: boolean;
}

export interface AppConfig {
  pillars: Record<string, string>;
  formats: Record<string, string>;
  surfaces: Record<string, string>;
  statuses: string[];
  status_labels: Record<string, string>;
  platforms: Record<string, string>;
  roles: string[];
  source_types: string[];
  pillar_targets: Record<string, number>;
  settings: Record<string, string>;
  anthropic_configured: boolean;
}

export interface Metric {
  id: number;
  content_id: number;
  captured_at: string | null;
  views: number | null;
  likes: number | null;
  avg_retention_pct: number | null;
  hook_retention_pct: number | null;
  rewatch_rate: number | null;
  saves: number | null;
  shares: number | null;
  comments: number | null;
  icp_comments: number | null;
  non_icp_comments: number | null;
  dm_keyword_triggers: number | null;
  fhs_clicks: number | null;
  fhs_purchases: number | null;
  save_rate: number | null;
  share_rate: number | null;
  icp_ratio: number | null;
  dm_fhs_rate: number | null;
}

export interface Content {
  id: number;
  idea_id: number | null;
  title: string | null;
  surface: string;
  format: string | null;
  pillar: string | null;
  status: string;
  script: string | null;
  hook: string | null;
  cta_keyword: string | null;
  notes: string | null;
  critic_score: number | null;
  scheduled_at: string | null;
  published_at: string | null;
  platform: string | null;
  external_url: string | null;
  created_by: number | null;
  created_at: string | null;
  asset_links: string[];
  idea_title: string | null;
  latest_metric: Metric | null;
  is_winner: boolean | null;
}

export interface ContentBrief {
  id: number;
  title: string | null;
  surface: string;
  format: string | null;
  status: string;
  critic_score: number | null;
  scheduled_at: string | null;
  published_at: string | null;
}

export interface Idea {
  id: number;
  title: string;
  angle: string | null;
  pillar: string | null;
  status: "proposed" | "approved" | "discarded";
  origin: "ai" | "manual";
  source_item_id: number | null;
  relevance_score: number | null;
  hook_draft: string | null;
  suggested_format: string | null;
  created_at: string | null;
  source_item: { id: number; title: string; url: string; snippet: string | null } | null;
  contents: ContentBrief[];
}

export interface Source {
  id: number;
  type: string;
  url: string;
  label: string;
  active: boolean;
  last_fetched_at: string | null;
  last_error: string | null;
}

export interface KpiOverview {
  primary: {
    avg_retention_pct: number | null;
    hook_retention_pct: number | null;
    rewatch_rate: number | null;
    save_rate: number | null;
    share_rate: number | null;
    icp_ratio: number | null;
    dm_fhs_rate: number | null;
    dm_keyword_triggers: number;
    fhs_clicks: number;
    fhs_purchases: number;
  };
  secondary: { views: number; likes: number };
  n_published: number;
  n_with_metrics: number;
  winner_ids: number[];
  missing_metrics: { id: number; title: string; published_at: string | null }[];
  trend: {
    week: string;
    n_posts: number;
    avg_retention_pct: number | null;
    hook_retention_pct: number | null;
    save_rate: number | null;
    share_rate: number | null;
    icp_ratio: number | null;
    views: number;
  }[];
}

export interface PillarMixRow {
  pillar: string;
  label: string;
  count: number;
  real_pct: number;
  target_pct: number;
  delta_pp: number;
  alert: boolean;
}

export interface PillarMix {
  total: number;
  rows: PillarMixRow[];
  alerts: string[];
  alert_threshold_pp: number;
}

export interface BreakdownRow {
  key: string;
  label: string;
  n_posts: number;
  n_with_metrics: number;
  avg_retention_pct: number | null;
  hook_retention_pct: number | null;
  rewatch_rate: number | null;
  save_rate: number | null;
  share_rate: number | null;
  icp_ratio: number | null;
  dm_fhs_rate: number | null;
  views: number;
  likes: number;
  winner_count: number;
  kill_flag: boolean;
  insufficient_sample: boolean;
  content_ids: number[];
}

export interface Breakdown {
  by: string;
  rows: BreakdownRow[];
  thresholds: {
    kill_retention_pct: number;
    kill_min_posts: number;
    format_min_posts: number;
    winner_retention_pct: number;
  };
}
