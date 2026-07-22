import type {
  Autofattura,
  Config,
  Health,
  JobInfo,
  ParseResponse,
  UploadResponse,
} from "./types";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {}
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => req<Health>("/health"),
  config: () => req<Config>("/config"),

  uploadFile: async (file: File): Promise<UploadResponse> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}/statements/upload`, { method: "POST", body: fd });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      throw new Error(j.detail || `Upload fallito (${res.status})`);
    }
    return res.json();
  },

  parse: (id: string) =>
    req<ParseResponse>(`/statements/${id}/parse`, { method: "POST" }),

  classify: (id: string) =>
    req<{ job_id: string }>(`/statements/${id}/classify`, { method: "POST" }),

  preview: (id: string) =>
    req<{ statement_id: string; autofatture: Autofattura[] }>(
      `/statements/${id}/preview`,
      { method: "POST" }
    ),

  job: (jobId: string) => req<JobInfo>(`/jobs/${jobId}`),

  createAutofatture: (autofatture: Autofattura[], dryRun = false) =>
    req<{ job_id: string }>(`/autofatture/create`, {
      method: "POST",
      body: JSON.stringify({ autofatture, dry_run: dryRun }),
    }),
};
