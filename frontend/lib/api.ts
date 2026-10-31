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

const UNREACHABLE = "Cannot reach the server. Check your connection.";

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
    return { status: 0, data: { detail: UNREACHABLE } as T };
  }
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  return { status: response.status, data: data as T };
}

// Posts a form with XMLHttpRequest, which (unlike fetch) reports upload
// progress: onProgress gets 0-100 while the file is being sent, then null once
// all of it has arrived and the server is processing it.
export function uploadWithProgress<T = any>(
  path: string,
  form: FormData,
  onProgress: (percent: number | null) => void,
): Promise<ApiResult<T>> {
  return new Promise((resolve) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/api/v1${path}`);
    const token = getToken();
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    request.upload.onload = () => onProgress(null);
    request.onload = () => {
      let data = null;
      try {
        data = JSON.parse(request.responseText);
      } catch {
        // not JSON: leave data null
      }
      resolve({ status: request.status, data });
    };
    request.onerror = () => resolve({ status: 0, data: { detail: UNREACHABLE } as T });
    request.send(form);
  });
}
