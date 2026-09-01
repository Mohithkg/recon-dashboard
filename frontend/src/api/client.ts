/**
 * API client wrapper.
 *
 * The JWT is held in memory (see auth/AuthContext.tsx) and injected into
 * every request via the `Authorization: Bearer` header.  We deliberately
 * avoid localStorage / sessionStorage so the token is never persisted to
 * disk or exposed to XSS via `localStorage.getItem`.
 */

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

let authToken: string | null = null;

/** Set the in-memory token (called by AuthContext on login / logout). */
export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Read the current in-memory token (useful for debugging). */
export function getAuthToken(): string | null {
  return authToken;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    const message =
      typeof detail === "string"
        ? detail
        : (detail as { detail?: string })?.detail ?? `HTTP ${status}`;
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: string;
  body?: FormData | string;
  headers?: Record<string, string>;
  /** Skip the default JSON Content-Type header. */
  skipContentType?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...opts.headers };

  // Attach JWT if available.
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  // Default to JSON content type unless skipped (e.g. file uploads).
  if (!opts.skipContentType && opts.body && typeof opts.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body,
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = await res.json();
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content or empty body
  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  /** POST with multipart/form-data (for file uploads). */
  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, {
      method: "POST",
      body: formData,
      skipContentType: true,
    }),
};
