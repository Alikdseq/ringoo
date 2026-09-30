import type { Manager } from '@/lib/api/services/stores.service';

export type ManagerManifestPhotos = string | string[];

let staticBySlugCache: Record<string, ManagerManifestPhotos> | null = null;

async function loadMenegersManifest(): Promise<Record<string, ManagerManifestPhotos>> {
  if (staticBySlugCache) return staticBySlugCache;
  try {
    const res = await fetch('/menegers/manifest.json', { cache: 'force-cache' });
    if (!res.ok) return {};
    const data = (await res.json()) as { managers?: Record<string, ManagerManifestPhotos> };
    staticBySlugCache = data.managers ?? {};
    return staticBySlugCache;
  } catch {
    return {};
  }
}

function manifestEntryToUrls(entry: ManagerManifestPhotos | undefined): string[] {
  if (!entry) return [];
  return Array.isArray(entry) ? entry : [entry];
}

export async function fetchManagerPhotosBySlug(slug: string): Promise<string[]> {
  const map = await loadMenegersManifest();
  return manifestEntryToUrls(map[slug]);
}

/** @deprecated Используйте fetchManagerPhotosBySlug */
export async function fetchManagerPhotoBySlug(slug: string): Promise<string | null> {
  const urls = await fetchManagerPhotosBySlug(slug);
  return urls[0] ?? null;
}

/** Имя в UI: две «л» в Эллина; полное ФИО для Джалилбека */
const DISPLAY_NAME_FIX: Record<string, string> = {
  'avakyan-ellina': 'Авакян Эллина',
  'авакян-элина': 'Авакян Эллина',
  'авакян-елина': 'Авакян Эллина',
  dzhalilbek: 'Джалилов Джалилбек',
  'джалилов-джалилбек': 'Джалилов Джалилбек',
};

/** manifest.json (латиница) ↔ slug из API (часто кириллица) */
const MANIFEST_SLUG_ALIASES: Record<string, string[]> = {
  'avakyan-ellina': ['авакян-элина', 'авакян-елина'],
  dzhalilbek: ['джалилов-джалилбек'],
  'авакян-элина': ['avakyan-ellina'],
  'авакян-елина': ['avakyan-ellina'],
  'джалилов-джалилбек': ['dzhalilbek'],
};

export function fixManagerDisplayName(manager: Manager): string {
  if (manager.slug && DISPLAY_NAME_FIX[manager.slug]) {
    return DISPLAY_NAME_FIX[manager.slug];
  }
  return manager.name;
}

const STATIC_BY_SLUG_SYNC: Record<string, ManagerManifestPhotos> = {};

/** Регистрирует URL после загрузки manifest (вызывается из AboutContent). */
export function registerManagerStaticPhotos(map: Record<string, ManagerManifestPhotos>) {
  Object.assign(STATIC_BY_SLUG_SYNC, map);
}

function manifestKeysForSlug(slug: string): string[] {
  const keys = new Set<string>([slug]);
  for (const alt of MANIFEST_SLUG_ALIASES[slug] ?? []) {
    keys.add(alt);
  }
  return [...keys];
}

export function getManagerStaticPhotoUrls(slug: string | undefined): string[] {
  if (!slug) return [];
  for (const key of manifestKeysForSlug(slug)) {
    const urls = manifestEntryToUrls(STATIC_BY_SLUG_SYNC[key]);
    if (urls.length > 0) return urls;
  }
  return [];
}

/** Фото из API или fallback public/menegers (после registerManagerStaticPhotos). */
export function getManagerPhotoUrl(manager: Manager): string | null {
  if (manager.photo) return manager.photo;
  const staticUrls = getManagerStaticPhotoUrls(manager.slug);
  return staticUrls[0] ?? null;
}
