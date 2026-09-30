/**
 * Канонический origin фронта (SEO: sitemap, robots).
 * Приоритет: NEXT_PUBLIC_SITE_URL → NEXT_PUBLIC_APP_URL → VERCEL_URL → localhost.
 */
export function getSiteUrl(): string {
  const explicit =
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, '') ||
    process.env.NEXT_PUBLIC_APP_URL?.replace(/\/+$/, '');
  if (explicit) return explicit;
  const vercel = process.env.VERCEL_URL?.replace(/\/+$/, '');
  if (vercel) return `https://${vercel}`;
  return 'http://localhost:3000';
}

/** База API v1: в Docker SSR ходит во внутренний URL (web:8000), в браузере — NEXT_PUBLIC_*. */
export function getApiV1BaseUrl(): string {
  const isServer = typeof window === 'undefined';
  const internal = process.env.API_INTERNAL_V1_URL?.trim();
  if (isServer && internal && process.env.VERCEL !== '1') {
    return internal.replace(/\/+$/, '');
  }
  if (process.env.VERCEL === '1' && process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL.replace(/\/+$/, '')}/api/v1`;
  }
  const u =
    process.env.NEXT_PUBLIC_API_V1_URL ??
    (process.env.NEXT_PUBLIC_API_URL
      ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '')}/api/v1`
      : 'http://localhost:8000/api/v1');
  return u.replace(/\/+$/, '');
}
