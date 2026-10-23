// The only place that talks HTTP. Feature repositories call `http`; nothing else uses fetch.
//
// Authentication is an HttpOnly session cookie set by the server; this code never sees it.
// Every state-changing request carries the X-CSRF-Token header from the current session.

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

let csrfToken: string | null = null;

/** Called by the auth repository whenever a session is loaded or ended. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

function messageFrom(data: unknown, status: number): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
    if (Array.isArray(detail)) return "Some fields are not valid";
  }
  return status >= 500 ? "The service is unavailable; try again" : `Request failed (${status})`;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  query?: Record<string, string | string[] | undefined>;
}

function withQuery(path: string, query: RequestOptions["query"]): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) {
      params.append(key, item);
    }
  }
  return params.size ? `${path}?${params.toString()}` : path;
}

export async function http<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const response = await fetch(`/api/v1${withQuery(path, options.query)}`, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data, messageFrom(data, response.status));
  return data as T;
}

export function tenantPath(tenantId: string, path: string): string {
  return `/tenants/${encodeURIComponent(tenantId)}${path}`;
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof ApiError && (status === undefined || error.status === status);
}
