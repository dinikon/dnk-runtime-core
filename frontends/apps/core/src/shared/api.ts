export class ApiError extends Error {
  constructor(public readonly status: number) {
    super(`API request failed (${status})`);
  }
}

let csrfToken = "";

export function setCsrfToken(token: string): void {
  csrfToken = token;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!path.startsWith("/api/")) {
    throw new Error("Only same-origin Core API paths are allowed.");
  }
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    if (!csrfToken) {
      const session = await apiRequest<{ csrfToken: string }>("/api/session/");
      setCsrfToken(session.csrfToken);
    }
    headers.set("X-CSRFToken", csrfToken);
  }
  const response = await fetch(path, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json() as Promise<T>;
}
