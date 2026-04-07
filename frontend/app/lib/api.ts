function apiBaseUrl(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").trim();
  return raw || "http://localhost:8000";
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

interface FetchOptions extends RequestInit {
  skipAuthRedirect?: boolean;
}

export async function apiFetch<T>(path: string, init?: FetchOptions): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const { skipAuthRedirect, ...fetchInit } = init ?? {};
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchInit?.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const base = apiBaseUrl().replace(/\/$/, "");
  const pathPart = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${base}${pathPart}`, { ...fetchInit, headers });

  if (res.status === 401) {
    if (!skipAuthRedirect && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    const body = await res.json().catch(() => ({}));
    throw new ApiError(401, body.detail ?? "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail) ?? res.statusText;
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
