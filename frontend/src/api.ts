const BASE: string = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    credentials: "same-origin",
    ...init,
    headers: { "Content-Type": "application/json", "X-MC-Client": "web", ...(init.headers || {}) },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail;
    throw new ApiError(res.status, typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data as T;
}

export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });

export function mediaUrl(path: string | null | undefined): string | undefined {
  return path ? BASE + path : undefined;
}

export function saveProgress(fileId: number, position: number, duration: number | null) {
  return fetch(`${BASE}/api/progress/${fileId}`, {
    method: "PUT",
    credentials: "same-origin",
    keepalive: true,
    headers: { "Content-Type": "application/json", "X-MC-Client": "web" },
    body: JSON.stringify({ position, duration }),
  }).catch(() => undefined);
}
