import type { ApiErrorResponse } from "./generated";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code?: string, public readonly requestId?: string) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  timeoutMs?: number;
  baseUrl?: string;
  skipAuthRefresh?: boolean;
};

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) { accessToken = token; }
export function getAccessToken() { return accessToken; }

const authenticationErrorCodes = new Set([
  "INVALID_TOKEN",
  "EXPIRED_TOKEN",
  "NOT_AUTHENTICATED",
  // Kept for compatibility with the backend's historical error-code typo.
  "NOT_AUTHNTICATED",
]);

function errorCode(payload: unknown) {
  const problem = payload as Partial<ApiErrorResponse>;
  return problem.error?.code;
}

export function isAuthenticationError(error: unknown): error is ApiError {
  return error instanceof ApiError && (
    authenticationErrorCodes.has(error.code ?? "")
    || (error.status === 401 && !error.code)
  );
}

function isAuthenticationResponse(response: Response, payload: unknown) {
  return response.status === 401 || authenticationErrorCodes.has(errorCode(payload) ?? "");
}

function getBaseUrl(override?: string) {
  const value = override ?? (typeof window === "undefined" ? process.env.API_URL : "/api/backend");
  if (!value) throw new ApiError("Не задан URL backend. Подключите API_URL и NEXT_PUBLIC_API_URL.", 503, "API_NOT_CONFIGURED");
  return value.replace(/\/$/, "");
}

function bodyAndHeaders(body: unknown, headers: HeadersInit | undefined) {
  if (body === undefined) return { body: undefined, headers };
  if (body instanceof URLSearchParams || body instanceof FormData || typeof body === "string" || body instanceof Blob) return { body: body as BodyInit, headers };
  return { body: JSON.stringify(body), headers: { "content-type": "application/json", ...headers } };
}

async function refreshAccessToken(baseUrl?: string): Promise<string | null> {
  if (typeof window === "undefined") return null;
  if (refreshPromise) return refreshPromise;
  refreshPromise = fetch("/api/auth/refresh", { method: "POST", credentials: "include", headers: { accept: "application/json" }, cache: "no-store" })
    .then(async (response) => {
      if (!response.ok) return null;
      const payload = await response.json() as { access_token?: string };
      if (!payload.access_token) return null;
      setAccessToken(payload.access_token);
      return payload.access_token;
    })
    .catch(() => null)
    .finally(() => { refreshPromise = null; });
  return refreshPromise;
}

function errorFromResponse(response: Response, payload: unknown, requestId?: string) {
  const problem = payload as Partial<ApiErrorResponse>;
  const code = problem.error?.code;
  const detail = problem.error?.detail;
  const message = isAuthenticationResponse(response, payload)
    ? "Сессия истекла. Войдите в систему снова."
    : response.status === 403
    ? "У вас нет доступа к этим данным. Проверьте роль и выбранную организацию."
    : (problem.error?.message ?? (typeof detail === "string" ? detail : undefined) ?? `Backend вернул ошибку ${response.status}`);
  return new ApiError(message, response.status, code, problem.request_id ?? requestId);
}

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { timeoutMs = 15_000, baseUrl, body, signal, headers, skipAuthRefresh = false, ...init } = options;
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort("timeout"), timeoutMs);
  const combinedSignal = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
  const prepared = bodyAndHeaders(body, headers);
  const requestHeaders: HeadersInit = { accept: "application/json", ...(accessToken ? { authorization: `Bearer ${accessToken}` } : {}), ...prepared.headers };
  try {
    const response = await fetch(`${getBaseUrl(baseUrl)}${path}`, { ...init, signal: combinedSignal, credentials: "include", headers: requestHeaders, body: prepared.body, cache: init.cache ?? "no-store" });
    const requestId = response.headers.get("x-request-id") ?? undefined;
    const payload = !response.ok ? await response.json().catch(() => ({})) : undefined;
    if (!skipAuthRefresh && !path.startsWith("/api/v1/auth/") && isAuthenticationResponse(response, payload)) {
      const refreshed = await refreshAccessToken(baseUrl);
      if (refreshed) return apiRequest<T>(path, { ...options, skipAuthRefresh: true });
      if (typeof window !== "undefined") {
        const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
        window.location.assign(`/signin?next=${next}`);
      }
    }
    if (!response.ok) {
      throw errorFromResponse(response, payload, requestId);
    }
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new ApiError("Backend не ответил вовремя. Повторите запрос.", 408, "TIMEOUT");
    throw new ApiError("Не удалось связаться с backend. Проверьте подключение к сети.", 0, "NETWORK_ERROR");
  } finally { clearTimeout(timer); }
}
