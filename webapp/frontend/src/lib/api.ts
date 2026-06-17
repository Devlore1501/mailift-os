const BASE = "/api";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function buildUrl(path: string, params?: Record<string, unknown>): string {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  if (!params) return url;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue;
    qs.append(k, String(v));
  }
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

async function parseResponse(res: Response): Promise<unknown> {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  return await res.text();
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await parseResponse(res);
    const detail =
      (body && typeof body === "object" && "detail" in (body as any)
        ? (body as any).detail
        : null) || res.statusText;
    throw new ApiError(
      typeof detail === "string" ? detail : `HTTP ${res.status}`,
      res.status,
      body
    );
  }
  return (await parseResponse(res)) as T;
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, unknown>
): Promise<T> {
  const res = await fetch(buildUrl(path, params), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  return handle<T>(res);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  params?: Record<string, unknown>
): Promise<T> {
  const res = await fetch(buildUrl(path, params), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return handle<T>(res);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(buildUrl(path), {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  return handle<T>(res);
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch(buildUrl(path), {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      body: form,
    });
    return handle<T>(res);
  } catch (err) {
    console.error("[apiUpload] fetch error", {
      path,
      filename: file.name,
      error: err instanceof Error ? err.message : String(err),
    });
    throw err;
  }
}

export function pdfUrl(relpath: string): string {
  // suppliers/invoices/{key}/{filename}
  const [key, ...rest] = relpath.split("/");
  return `${BASE}/suppliers/invoices/${encodeURIComponent(key)}/${rest
    .map(encodeURIComponent)
    .join("/")}`;
}

export function rejectPdfUrl(relpath: string): string {
  return `${BASE}/suppliers/verify-rejects/${relpath
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}
