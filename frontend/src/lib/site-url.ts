/**
 * Канонический origin фронта (SEO: sitemap, robots).
 * Приоритет: NEXT_PUBLIC_SITE_URL → NEXT_PUBLIC_APP_URL → публичный домен Vercel → localhost.
 */
function vercelHost(raw: string | undefined): string | null {
  const host = raw?.trim().replace(/^https?:\/\//, '').replace(/\/+$/, '');
  return host || null;
}

/** Публичный origin. VERCEL_URL — адрес конкретного деплоя, он часто закрыт Vercel Authentication. */
function vercelPublicOrigin(): string | null {
  if (process.env.VERCEL !== '1') return null;
  const production = vercelHost(process.env.VERCEL_PROJECT_PRODUCTION_URL);
  if (production) return `https://${production}`;
  const deployment = vercelHost(process.env.VERCEL_URL);
  if (deployment) return `https://${deployment}`;
  return null;
}

export function getSiteUrl(): string {
  const explicit =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, '') ||
    process.env.NEXT_PUBLIC_APP_URL?.replace(/\/+$/, '');
  if (explicit) return explicit;
  return vercelPublicOrigin() ?? 'http://localhost:3000';
}

/** База API v1: в Docker SSR ходит во внутренний URL (web:8000), в браузере — NEXT_PUBLIC_*. */
export function getApiV1BaseUrl(): string {
  const isServer = typeof window === 'undefined';
  const internal = process.env.API_INTERNAL_V1_URL?.trim();
  if (isServer && internal && process.env.VERCEL !== '1') {
    return internal.replace(/\/+$/, '');
  }
  const vercelOrigin = isServer ? vercelPublicOrigin() : null;
  if (vercelOrigin) return `${vercelOrigin}/api/v1`;
  const u =
    process.env.NEXT_PUBLIC_API_V1_URL ??
    (process.env.NEXT_PUBLIC_API_URL
      ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '')}/api/v1`
      : 'http://localhost:8000/api/v1');
  return u.replace(/\/+$/, '');
}
