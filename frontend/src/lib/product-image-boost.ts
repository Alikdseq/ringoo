const IPHONE_PREFIX = 'iphone-';

/**
 * Импорт: `product_slug = f"{brand}-{model_slug}"`, у Apple `model_slug` часто уже
 * `iphone-17-pro` → в БД `iphone-iphone-17-pro`. Снимаем все ведущие `iphone-`.
 */
export function iphoneProductModelTail(slug: string): string | null {
  let s = slug.trim().toLowerCase();
  if (!s.startsWith(IPHONE_PREFIX)) {
    return null;
  }
  while (s.startsWith(IPHONE_PREFIX)) {
    s = s.slice(IPHONE_PREFIX.length);
  }
  return s || null;
}

export type CatalogImageVisualMode =
  | 'samsung-cover'
  | 'iphone-mega-cover'
  | 'iphone-compact-contain'
  | 'contain';

/**
 * Mega: 17e / 17 Pro / Max / Air / 17 (+Plus), базовый 16 (+Plus) — крупнее всех.
 * Compact: 16e, 16 Pro/Max, 15, 13 — чуть меньше остальных iPhone.
 */
/**
 * Только модели из ТЗ: 17e, 17 Pro Max, 17 Pro, 17 Air, 17, 16 (базовый).
 * 16e / 16 Pro / 16 Pro Max и остальные — без спец-обработки.
 */
export function isTargetIphoneGallerySlug(slug: string, categorySlug?: string | null): boolean {
  const cat = categorySlug?.trim().toLowerCase() ?? '';
  const t = iphoneProductModelTail(slug);
  if (t == null && cat !== 'iphone') return false;
  if (t == null) return false;

  if (t.startsWith('17-pro-max')) return true;
  if (t.startsWith('17-pro')) return true;
  if (t.startsWith('17-air')) return true;
  if (t.startsWith('17-e') || /^17e($|-)/.test(t)) return true;
  if (t === '17' || t.startsWith('17-plus')) return true;
  if (t === '16' || t.startsWith('16-plus')) return true;

  return false;
}

export const IPHONE_TARGET_PDP_HERO_0 =
  'object-cover object-center origin-center scale-[1.38] sm:scale-[1.48]';
export const IPHONE_TARGET_PDP_HERO_1 =
  'object-cover object-center origin-center scale-[1.32] sm:scale-[1.42]';

export function getCatalogImageVisualMode(
  slug: string,
  categorySlug?: string | null
): CatalogImageVisualMode {
  const s = slug.trim().toLowerCase();
  const cat = categorySlug?.trim().toLowerCase() ?? '';

  if (cat === 'samsung' || s.startsWith('samsung-')) {
    return 'samsung-cover';
  }
  if (cat !== '' && cat !== 'iphone') {
    return 'contain';
  }

  const t = iphoneProductModelTail(slug);
  if (t == null) {
    return 'contain';
  }

  if (t.startsWith('17-pro-max')) return 'iphone-mega-cover';
  if (t.startsWith('17-pro')) return 'iphone-mega-cover';
  if (t.startsWith('17-air')) return 'iphone-mega-cover';
  if (t.startsWith('17-e') || /^17e($|-)/.test(t)) return 'iphone-mega-cover';
  if (t === '17' || t.startsWith('17-plus')) return 'iphone-mega-cover';

  if (t.startsWith('16e') || t.startsWith('16-e')) return 'iphone-compact-contain';
  if (t.startsWith('16-pro-max')) return 'iphone-compact-contain';
  if (t.startsWith('16-pro')) return 'iphone-compact-contain';
  if (t === '16' || t.startsWith('16-plus')) return 'iphone-mega-cover';

  if (t.startsWith('15')) return 'iphone-compact-contain';
  if (t.startsWith('13')) return 'iphone-compact-contain';

  if (t.startsWith('16')) return 'iphone-compact-contain';

  return 'contain';
}

export const IPHONE_BOOST_CARD_IMAGE_CLASS =
  'object-cover object-center origin-center scale-[1.26] sm:scale-[1.34]';

export const IPHONE_COMPACT_CARD_IMAGE_CLASS =
  'object-contain object-center origin-center scale-[0.9] sm:scale-[0.93]';

export const IPHONE_MEGA_PDP_IMAGE_IDLE_CLASS =
  'object-cover object-center origin-center scale-[1.1] sm:scale-[1.14]';
export const IPHONE_MEGA_PDP_IMAGE_ZOOM_CLASS =
  'object-cover object-center origin-center scale-[1.28] sm:scale-[1.36]';

export const IPHONE_COMPACT_PDP_IMAGE_IDLE_CLASS =
  'object-contain object-center origin-center scale-[0.92] sm:scale-[0.95]';
export const IPHONE_COMPACT_PDP_IMAGE_ZOOM_CLASS =
  'object-contain object-center origin-center scale-105 sm:scale-110';

/** Карточка каталога */
export function catalogCardImageClassName(slug: string, categorySlug?: string | null): string {
  const mode = getCatalogImageVisualMode(slug, categorySlug);
  if (mode === 'samsung-cover') {
    return 'object-cover object-center';
  }
  if (mode === 'iphone-mega-cover') {
    return IPHONE_BOOST_CARD_IMAGE_CLASS;
  }
  if (mode === 'iphone-compact-contain') {
    return IPHONE_COMPACT_CARD_IMAGE_CLASS;
  }
  return 'object-contain object-center';
}
