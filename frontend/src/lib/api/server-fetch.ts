/**
 * Server-side fetch к Django во внутренней Docker-сети (http://web:8000).
 * Публичный HTTPS остаётся на reverse proxy; Django с TRUST_PROXY + SECURE_SSL_REDIRECT
 * принимает запрос как secure только при X-Forwarded-Proto: https.
 */

const DEFAULT_TIMEOUT_MS = 10_000;

export type ServerFetchInit = RequestInit & {
  next?: { revalidate?: number | false; tags?: string[] };
  timeoutMs?: number;
};

/** true, когда SSR ходит на внутренний HTTP API (не публичный HTTPS / Vercel). */
export function usesInternalDjangoHttp(): boolean {
  if (process.env.VERCEL === '1') return false;
  const internal = process.env.API_INTERNAL_V1_URL?.trim();
  // Только явный Docker-internal http://… (не https:// публичный origin).
  return Boolean(internal && /^http:\/\//i.test(internal));
}

export function buildInternalDjangoFetchInit(init: ServerFetchInit = {}): ServerFetchInit {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (usesInternalDjangoHttp()) {
    headers.set('X-Forwarded-Proto', 'https');
  }

  let signal = rest.signal;
  if (!signal && typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    signal = AbortSignal.timeout(timeoutMs);
  }

  return { ...rest, headers, signal };
}

export async function fetchInternalJson<T>(
  url: string,
  fallback: T,
  init: ServerFetchInit = {}
): Promise<T> {
  try {
    const res = await fetch(url, buildInternalDjangoFetchInit(init));
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}
