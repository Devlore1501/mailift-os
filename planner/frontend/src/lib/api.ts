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
    if (v === undefined || v === null || v === "") continue;
    qs.append(k, String(v));
  }
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

async function parseResponse(res: Response): Promise<unknown> {
  if (res.status === 204) return null;
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

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
  path: string,
  body?: unknown,
  params?: Record<string, unknown>
): Promise<T> {
  const res = await fetch(buildUrl(path, params), {
    method,
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return handle<T>(res);
}

export function apiGet<T>(
  path: string,
  params?: Record<string, unknown>
): Promise<T> {
  return request<T>("GET", path, undefined, params);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

export function apiDelete<T = null>(path: string): Promise<T> {
  return request<T>("DELETE", path);
}

/** POST multipart (upload file). Il Content-Type lo imposta il browser. */
export async function apiUpload<T>(
  path: string,
  formData: FormData,
  params?: Record<string, unknown>
): Promise<T> {
  const res = await fetch(buildUrl(path, params), {
    method: "POST",
    headers: { Accept: "application/json" },
    body: formData,
  });
  return handle<T>(res);
}
