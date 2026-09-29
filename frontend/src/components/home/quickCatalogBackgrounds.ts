/** Фоны кнопок быстрого каталога: `public/catologfon/{slug}f.jpg` */
export const QUICK_CATALOG_BG_BY_SLUG: Record<string, string> = {
  iphone: '/catologfon/iphonef.jpg',
  huawei: '/catologfon/huaweif.jpg',
  realme: '/catologfon/realmef.jpg',
  samsung: '/catologfon/samsungf.jpg',
  xiaomi: '/catologfon/xiaomif.jpg',
  tecno: '/catologfon/tecnof.jpg',
  infinix: '/catologfon/infinixf.jpg',
};

export function quickCatalogBackgroundForSlug(slug: string): string | undefined {
  const key = slug.trim().toLowerCase();
  return QUICK_CATALOG_BG_BY_SLUG[key];
}

/**
 * Единая «съёмка»: фото ярче, без затемнения. На hover чуть «оживает»
 * (лёгкое увеличение, насыщенность). Затемняющие фильтры убраны.
 */
export const QUICK_CATALOG_IMAGE_CLASS =
  'object-cover object-[52%_38%] scale-[1.06] saturate-[1.08] contrast-[1.04] transition-[transform,filter] duration-500 ease-out group-hover:scale-[1.12] group-hover:saturate-[1.18] group-hover:contrast-[1.08]';

/**
 * Внешняя оболочка кнопки. Включает 3D-tilt при hover на устройствах с указателем.
 * Mobile (no-hover): только лёгкое active-scale без 3D.
 */
export const QUICK_CATALOG_SHELL_CLASS = [
  'relative h-full w-full overflow-hidden rounded-2xl ring-1 ring-white/20 sm:rounded-3xl',
  'shadow-[0_6px_18px_rgba(0,0,0,0.16)]',
  'will-change-transform [transform-style:preserve-3d] [perspective:1000px]',
  'transition-[transform,box-shadow,filter] duration-[360ms] ease-[cubic-bezier(.2,.8,.2,1)]',
  // 3D hover только там, где есть hover (desktop / tablet с мышью)
  '[@media(hover:hover)]:group-hover:-translate-y-1.5',
  '[@media(hover:hover)]:group-hover:[transform:translateY(-6px)_rotateX(2deg)_rotateY(-2deg)_scale(1.025)]',
  '[@media(hover:hover)]:group-hover:shadow-[0_18px_44px_rgba(0,0,0,0.25),0_0_28px_rgba(255,255,255,0.10)]',
  '[@media(hover:hover)]:group-hover:ring-white/40',
  'group-active:translate-y-0 group-active:scale-[0.99]',
].join(' ');

/** Лёгкий top-glow только сверху — добавляет «3D-объём» без затемнения. */
export const QUICK_CATALOG_LIGHT_OVERLAY_CLASS =
  'pointer-events-none absolute inset-0 bg-[linear-gradient(155deg,rgba(255,255,255,0.18)_0%,rgba(255,255,255,0.04)_28%,transparent_55%)] mix-blend-overlay';

/** Тонкая виньетка только в нижней четверти — под текстом, чтобы он читался. */
export const QUICK_CATALOG_SCRIM_CLASS =
  'pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-[linear-gradient(to_top,rgba(0,0,0,0.45)_0%,rgba(0,0,0,0.18)_45%,transparent_100%)]';

/** Без затемнения (раньше был backdrop-blur). Оставляем класс для совместимости. */
export const QUICK_CATALOG_FROST_CLASS =
  'pointer-events-none absolute inset-0 opacity-0';

/** Glow по краям при hover — усиливает 3D-эффект без перекрытия фото. */
export const QUICK_CATALOG_GLOW_CLASS = [
  'pointer-events-none absolute -inset-3 rounded-[inherit] opacity-0',
  'bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,0.45),transparent_55%)]',
  'transition-opacity duration-500',
  '[@media(hover:hover)]:group-hover:opacity-80',
].join(' ');

/** Подпись: яркое тиснение и тень — без затемняющей подложки. */
export const QUICK_CATALOG_LABEL_CLASS = [
  'absolute inset-x-0 bottom-0 z-10 flex items-end justify-center px-3 pb-3 sm:pb-4',
  'text-center font-bold leading-tight tracking-tight text-white',
  'drop-shadow-[0_2px_6px_rgba(0,0,0,0.55)] drop-shadow-[0_1px_2px_rgba(0,0,0,0.65)]',
  'transition-[transform,text-shadow] duration-300',
  '[@media(hover:hover)]:group-hover:drop-shadow-[0_3px_10px_rgba(0,0,0,0.7)]',
].join(' ');
