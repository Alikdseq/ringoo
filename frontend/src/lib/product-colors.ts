import type { ProductColor, ProductListColor } from '@/types';

/**
 * Соответствует backend `canonical_color_slug`: объединяет cam, button/full N,
 * back/front, префикс iphone-*- в slug цвета.
 */
export function canonicalColorSlug(slug: string): string {
  let s = slug
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  let prevOuter = '';
  while (prevOuter !== s) {
    prevOuter = s;
    let prev = '';
    while (prev !== s) {
      prev = s;
      s = s.replace(/-button-\d+$/i, '');
      s = s.replace(/-full-\d+$/i, '');
      s = s.replace(/-full$/i, '');
      s = s.replace(/-cam(s)?$/i, '');
      s = s.replace(/-came$/i, '');
      s = s.replace(/-back$/i, '');
      s = s.replace(/-front$/i, '');
      s = s.replace(/-side$/i, '');
      s = s.replace(/-product$/i, '');
      s = s.replace(/-\d{1,2}$/i, '');
      s = s.replace(/-+$/g, '').replace(/^-+/g, '');
    }
    s = s.replace(/^(back|front)-/i, '');
    s = s.replace(/^(cam|full|side)(-\d+)?-/i, '');
    s = s.replace(/^iphone-\d{1,2}e?(?:-(?:pro-max|pro|plus|air))*-/i, '');
    s = s.replace(/^iphone-/i, '');
    s = s.replace(/-+/g, '-').replace(/^-|-$/g, '');
  }
  return (s || slug).toLowerCase();
}

function cleanDisplayLabel(label: string): string {
  return label
    .replace(/^iphone\s*\d{1,2}e?\s*(pro\s*max|pro|plus|air)?\s*/i, '')
    .replace(/\s*button\s*\d+/gi, '')
    .replace(/\s*full\s*\d+/gi, '')
    .replace(/\s+cam\b/gi, '')
    .replace(/^\s*back\s+/gi, '')
    .replace(/\s+back\s*$/gi, '')
    .replace(/^\s*front\s+/gi, '')
    .replace(/\s+front\s*$/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export interface MergedColorGroup {
  key: string;
  /** Все ProductColor.id, относящиеся к одному оттенку */
  colorIds: string[];
  label: string;
  hex: string | null;
  sortOrder: number;
}

/** Одна кнопка цвета в UI: объединяет варианты съёмки / дубликаты slug. */
export function mergeColorGroups(colors: ProductColor[]): MergedColorGroup[] {
  const m = new Map<string, MergedColorGroup>();
  for (const c of colors) {
    if (c.is_active === false) continue;
    const key = canonicalColorSlug(c.slug);
    const ex = m.get(key);
    const cleanLabel = cleanDisplayLabel(c.label) || c.label;
    if (!ex) {
      m.set(key, {
        key,
        colorIds: [c.id],
        label: cleanLabel,
        hex: c.hex,
        sortOrder: c.sort_order ?? 0,
      });
    } else {
      ex.colorIds.push(c.id);
      const exHasNoise = /\b(button|full|cam|back|front)\b/i.test(ex.label);
      const newClean = cleanLabel;
      const newHasNoise = /\b(button|full|cam)\b/i.test(c.label);
      if ((exHasNoise && !newHasNoise) || (!newHasNoise && newClean.length < ex.label.length)) {
        ex.label = newClean;
        ex.hex = c.hex ?? ex.hex;
      }
      ex.sortOrder = Math.min(ex.sortOrder, c.sort_order ?? 0);
    }
  }
  return [...m.values()].sort(
    (a, b) => a.sortOrder - b.sortOrder || a.label.localeCompare(b.label, 'ru')
  );
}

/** Для карточки каталога: один ряд цвета + лучшее превью из группы. */
export function mergeListColorsForCard(colors: ProductListColor[]): ProductListColor[] {
  if (!colors.length) return [];
  const groups = mergeColorGroups(colors);
  return groups.map(g => {
    const members = colors.filter(c => g.colorIds.includes(c.id));
    const primaryId = g.colorIds[0]!;
    const primary = members.find(c => c.id === primaryId) ?? members[0]!;
    const withPreview =
      members.find(c => c.id === primaryId && c.preview_image) ??
      members.find(c => c.preview_image) ??
      primary;
    return {
      ...withPreview,
      id: primaryId,
      slug: g.key,
      label: g.label,
      hex: g.hex ?? withPreview.hex,
      sort_order: g.sortOrder,
      preview_image: withPreview.preview_image ?? null,
      preview_alt: withPreview.preview_alt ?? g.label,
    };
  });
}

const COLOR_SWATCH_HEX_HINTS: Record<string, string> = {
  black: '#1C1C1E',
  'titanium-black': '#2C2C2E',
  'titanium-gray': '#8E8E93',
  'titanium-silverblue': '#A8C8E0',
  'titanium-whitesilver': '#E8E8ED',
  white: '#F5F5F7',
  silver: '#C0C0C0',
  gray: '#8E8E93',
  grey: '#8E8E93',
  blue: '#007AFF',
  pink: '#F2B8C6',
  red: '#C62828',
  green: '#34C759',
  purple: '#AF52DE',
  gold: '#E6C200',
  yellow: '#FFCC00',
  teal: '#5AC8D0',
  ultramarine: '#3A5BA0',
  natural: '#D4C4B0',
  desert: '#C4A574',
  starlight: '#E3E3E8',
  midnight: '#1F2933',
  skyblue: '#5EB3E8',
  orange: '#f97316',
  'orange-titanium': '#f97316',
  'cosmic-orange': '#f97316',
  'titanium-orange': '#f97316',
  graphite: '#4B5563',
  rosegold: '#E8B4B8',
  'rose-gold': '#E8B4B8',
  lavender: '#C4B5FD',
  iceblue: '#7DD3FC',
  'ice-blue': '#7DD3FC',
  charcoal: '#36454F',
  cobaltviolet: '#6D28D9',
  'cobalt-violet': '#6D28D9',
  pinkgold: '#E8B4B8',
  'pink-gold': '#E8B4B8',
  blackyellow: '#1C1C1E',
  'black-yellow': '#1C1C1E',
  mint: '#6EE7B7',
  navy: '#1E3A5F',
  violet: '#7C3AED',
  sage: '#9CAF88',
  mistblue: '#93C5FD',
  silvershadow: '#C0C0C0',
  'silver-shadow': '#C0C0C0',
};

const FALLBACK_SWATCH_HEX = '#d4d4d8';

function isValidHex(hex: string | null | undefined): hex is string {
  return Boolean(hex && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(hex));
}

/** HEX для кружка цвета: API hex или подсказка по slug/label (оранж и др.). */
export function resolveColorSwatchHex(color: {
  hex?: string | null;
  slug?: string;
  label?: string;
}): string {
  if (isValidHex(color.hex)) return color.hex;
  const slug = (color.slug ?? '').toLowerCase();
  const label = (color.label ?? '').toLowerCase();
  if (COLOR_SWATCH_HEX_HINTS[slug]) return COLOR_SWATCH_HEX_HINTS[slug]!;
  for (const [key, hx] of Object.entries(COLOR_SWATCH_HEX_HINTS)) {
    if (slug.includes(key) || label.includes(key)) return hx;
  }
  if (
    label.includes('orange') ||
    slug.includes('orange') ||
    label.includes('оранж') ||
    slug.includes('oranzh')
  ) {
    return '#f97316';
  }
  return FALLBACK_SWATCH_HEX;
}

export function filterImagesForColorGroups<T extends { color?: { id: string } | null | undefined }>(
  allImages: T[],
  colorIds: Set<string>
): T[] {
  const forColor = allImages.filter(img => img.color?.id && colorIds.has(img.color.id));
  const common = allImages.filter(img => !img.color);
  const merged = [...forColor, ...common];
  return merged.length ? merged : allImages;
}
