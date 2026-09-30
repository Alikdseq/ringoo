/** Upstream Django for same-origin /api/v1 and /media (ngrok demo, Docker). */
export function getApiProxyTarget(): string | null {
  const raw = process.env.RINGOO_API_PROXY_TARGET?.trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, '');
}
