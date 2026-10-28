// Calls the API through this app's /api rewrite. The token is kept in
// sessionStorage, so it is gone when the tab closes and is never a cookie.
const TOKEN_KEY = "upskill.token";

export type ApiResult<T = unknown> = { status: number; data: T };

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

type Options = { method?: string; json?: unknown; form?: FormData };

// Status 0 means the server could not be reached.
export async function api<T = any>(
  path: string,
  { method = "GET", json, form }: Options = {},
): Promise<ApiResult<T>> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined = form;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body });
  } catch {
    return {
      status: 0,
      data: { detail: "Cannot reach the server. Check your connection." } as T,
    };
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  return { status: response.status, data: data as T };
}
