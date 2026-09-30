/**
 * Собирает полный URL для медиа (изображения товаров и т.д.).
 * API может возвращать относительный путь (/media/...) или абсолютный localhost/web:8000.
 */

const DOCKER_INTERNAL_HOST =
  /^(?:https?:\/\/)?(?:web|ringoo_backend|host\.docker\.internal)(?::\d+)?(?=\/|$)/i;

const LOCAL_API_ORIGIN =
  /^https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0)(?::\d+)?$/i;

function publicSiteOrigin(): string {
  const site =
    process.env.NEXT_PUBLIC_SITE_URL?.trim() ||
    process.env.NEXT_PUBLIC_APP_URL?.trim() ||
    '';
  return site.replace(/\/+$/, '');
}

function publicApiMediaBase(): string {
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL ??
    process.env.NEXT_PUBLIC_API_V1_URL?.replace(/\/api\/v1\/?$/i, '') ??
    'http://localhost:8000';
  const apiOrigin = apiBase.replace(/\/+$/, '');
  const siteOrigin = publicSiteOrigin();
  if (siteOrigin && (apiOrigin === siteOrigin || LOCAL_API_ORIGIN.test(apiOrigin))) {
    return siteOrigin;
  }
  return apiOrigin;
}

/** Ngrok / same-origin: медиа только как /media/... (прокси Next → Django). */
function preferRelativeMedia(): boolean {
  const site = publicSiteOrigin();
  if (!site) return false;
  if (site.includes('ngrok-free.dev') || site.includes('ngrok.app')) return true;
  if (process.env.RINGOO_NGROK_DEMO === '1') return true;
  const api = publicApiMediaBase();
  return api === site || LOCAL_API_ORIGIN.test(api);
}

/** http(s)://localhost:8000/media/x → /media/x */
function localMediaToRelative(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (!LOCAL_API_ORIGIN.test(parsed.origin)) return null;
    if (!parsed.pathname.startsWith('/media/')) return null;
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return null;
  }
}

/** Заменяет http://web:8000/... на публичный origin или относительный путь. */
export function normalizeMediaUrl(url: string): string {
  if (!url) return url;

  const fromLocal = localMediaToRelative(url);
  if (fromLocal && preferRelativeMedia()) return fromLocal;

  if (!DOCKER_INTERNAL_HOST.test(url)) {
    return url;
  }

  const base = publicApiMediaBase();
  try {
    const parsed = new URL(url, base);
    if (DOCKER_INTERNAL_HOST.test(parsed.origin)) {
      const path = `${parsed.pathname}${parsed.search}`;
      if (preferRelativeMedia() && path.startsWith('/media/')) return path;
      return `${base}${path}`;
    }
  } catch {
    const replaced = url.replace(DOCKER_INTERNAL_HOST, base);
    const rel = localMediaToRelative(replaced);
    if (rel && preferRelativeMedia()) return rel;
    return replaced;
  }
  return url;
}

export function getMediaUrl(path: string | undefined): string {
  if (!path) return '';
  let trimmed = path.trim();
  if (!trimmed) return '';

  trimmed = normalizeMediaUrl(trimmed);

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    const relative = localMediaToRelative(trimmed);
    if (relative && preferRelativeMedia()) return relative;

    // Никогда не поднимать localhost до https — иначе ERR_SSL_PROTOCOL_ERROR
    if (LOCAL_API_ORIGIN.test(trimmed)) {
      const rel = localMediaToRelative(trimmed.replace(/^https:\/\//i, 'http://'));
      if (rel) return rel;
      return trimmed.replace(/^https:\/\//i, 'http://');
    }

    const site = publicSiteOrigin();
    if (site && preferRelativeMedia()) {
      try {
        const parsed = new URL(trimmed);
        if (parsed.pathname.startsWith('/media/')) {
          return `${parsed.pathname}${parsed.search}`;
        }
      } catch {
        /* ignore */
      }
    }

    if (
      process.env.NODE_ENV === 'production' &&
      trimmed.startsWith('http://') &&
      !LOCAL_API_ORIGIN.test(trimmed)
    ) {
      return trimmed.replace(/^http:\/\//i, 'https://');
    }
    return trimmed;
  }

  if (trimmed.startsWith('/') && !trimmed.startsWith('/media/')) {
    return trimmed;
  }

  if (trimmed.startsWith('/media/') && preferRelativeMedia()) {
    return trimmed;
  }

  const base = publicApiMediaBase();
  const url = trimmed.startsWith('/') ? base + trimmed : `${base}/${trimmed}`;
  return normalizeMediaUrl(url);
}

export function shouldUnoptimizeImage(src: string): boolean {
  if (src.startsWith('/media/')) return true;
  if (preferRelativeMedia()) return true;
  if (process.env.NODE_ENV === 'production') return false;
  const normalized = normalizeMediaUrl(src);
  return (
    normalized.startsWith('http://127.0.0.1') ||
    normalized.startsWith('http://localhost')
  );
}
