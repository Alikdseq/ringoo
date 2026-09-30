/**
 * DESIGN_SPEC §4: Spacing и Layout
 *
 * Соответствие Tailwind spacing:
 *   xs  = 4px  → p-1, m-1, gap-1, space-1
 *   sm  = 8px  → p-2, m-2, gap-2, space-2
 *   md  = 16px → p-4, m-4, gap-4, space-4
 *   lg  = 24px → p-6, m-6, gap-6, space-6
 *   xl  = 32px → p-8, m-8, gap-8, space-8
 *   2xl = 48px → p-12, m-12, gap-12, space-12
 *
 * Max-width контента: 1280px → max-w-6xl (или max-w-[1280px])
 *
 * Боковые отступы по breakpoints:
 *   mobile (< 640px):  px-4  (16px)
 *   tablet (≥ 768px):  px-6  (24px)
 *   desktop (≥ 1024px): px-8 (32px)
 *
 * Breakpoints (Tailwind): 640, 768, 1024, 1280
 */

export const SPACING = {
  xs: '0.25rem' /* 4px */,
  sm: '0.5rem' /* 8px */,
  md: '1rem' /* 16px */,
  lg: '1.5rem' /* 24px */,
  xl: '2rem' /* 32px */,
  '2xl': '3rem' /* 48px */,
} as const;

export const CONTAINER_MAX_WIDTH = '1280px';

/** Стандартный контейнер витрины (1280px) */
export const CONTAINER_CLASS = 'mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8';

/** Каталог, акции — 1280px + чуть шире на xl */
export const CONTAINER_WIDE_CLASS =
  'mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8';

/** Фиксированный хедер — без подложки, только «таблетка» */
export const HEADER_FIXED_CLASS =
  'fixed inset-x-0 top-0 z-[100] w-full max-w-full bg-transparent pt-[env(safe-area-inset-top,0px)]';

/** Отступ main под фиксированный хедер (+ safe-area) */
export const HEADER_MAIN_OFFSET_CLASS =
  'pt-[calc(5.5rem+env(safe-area-inset-top,0px))] sm:pt-[calc(6rem+env(safe-area-inset-top,0px))] md:pt-[calc(6.5rem+env(safe-area-inset-top,0px))]';

/** Оболочка хедера — те же боковые отступы */
export const HEADER_OUTER_CLASS =
  'mx-auto box-border w-full max-w-[1600px] px-2 py-2 sm:px-4 sm:py-3 md:px-6 md:py-4';

/** Внутренняя «таблетка» хедера */
export const HEADER_PILL_CLASS =
  'box-border w-full max-w-full rounded-full border-2 border-[var(--color-brand)] bg-white shadow-[0_0_0_1px_rgba(34,197,94,0.35),0_0_18px_rgba(34,197,94,0.28),0_0_42px_rgba(34,197,94,0.14)]';

/** Сетка карточек товара: 1 col mobile, 2 md, 3 lg */
export const PRODUCT_CARD_GRID_CLASS =
  'grid grid-cols-1 gap-4 sm:gap-5 md:grid-cols-2 md:gap-6 lg:grid-cols-3 lg:gap-7';

/** Иконки хедера: компакт на узких экранах, стабильный размер на md+ */
export const HEADER_ICON_BUTTON_CLASS =
  'relative inline-flex max-[399px]:min-h-9 max-[399px]:min-w-9 max-[399px]:[&_svg]:h-[18px] max-[399px]:[&_svg]:w-[18px] min-h-10 min-w-10 shrink-0 touch-manipulation items-center justify-center rounded-lg transition-colors hover:bg-zinc-100/80 md:min-h-11 md:min-w-11 md:rounded-xl md:[&_svg]:h-5 md:[&_svg]:w-5';

/** Логотип + «Каталог» — одна компактная группа слева */
export const HEADER_BRAND_CLUSTER_CLASS =
  'inline-flex shrink-0 items-center gap-1.5 overflow-visible sm:gap-2';

/** Внутренняя раскладка «таблетки»: mobile flex, desktop 3 колонки */
export const HEADER_PILL_INNER_CLASS =
  'flex w-full min-w-0 items-center justify-between gap-2 py-2 pl-2 pr-1 sm:pl-2.5 sm:pr-1.5 md:grid md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-center md:gap-x-4 md:px-5 md:py-2.5 lg:gap-x-6 lg:px-6 lg:py-3';

/** Центральное меню (desktop) */
export const HEADER_NAV_CLASS =
  'hidden min-w-0 flex-nowrap items-center justify-center gap-x-3 px-2 text-sm font-semibold text-foreground md:flex lg:gap-x-5 lg:text-[15px] xl:gap-x-6';

/** Правая зона: поиск, переключатель, иконки */
export const HEADER_ACTIONS_CLUSTER_CLASS =
  'flex min-w-0 shrink-0 items-center justify-end gap-1.5 md:gap-2 lg:gap-3';

/** Ряд иконок избранное / корзина / бургер */
export const HEADER_ICONS_ROW_CLASS =
  'flex shrink-0 items-center gap-0.5 md:gap-1.5 lg:gap-2 md:pl-0.5';

/** Размер логотипа: mobile чуть крупнее, desktop сбалансированный */
export const HEADER_LOGO_BOX_CLASS =
  'h-12 w-[min(108px,34vw)] max-w-[34vw] shrink-0 max-[399px]:-mr-0.5 sm:h-[3.25rem] sm:w-[7.75rem] sm:max-w-none md:h-14 md:w-[8.25rem] lg:h-[4.25rem] lg:w-[9.25rem]';

/** Кнопка «Каталог» в хедере — текст всегда виден */
export const HEADER_CATALOG_BUTTON_CLASS =
  'inline-flex shrink-0 items-center gap-1 rounded-full bg-[var(--color-brand)] font-semibold text-white transition-all duration-200 touch-manipulation hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand)] focus-visible:ring-offset-2 focus-visible:ring-offset-white h-9 min-h-9 px-2 text-[10px] leading-none max-[399px]:[&_svg]:h-3.5 max-[399px]:[&_svg]:w-3.5 sm:h-10 sm:gap-1.5 sm:px-2.5 sm:text-[11px] sm:[&_svg]:h-4 sm:[&_svg]:w-4 md:h-auto md:min-h-0 md:gap-1.5 md:px-4 md:py-2.5 md:text-base md:[&_svg]:h-5 md:[&_svg]:w-5';

/** Бейдж на иконке (внутри кнопки, без отрицательных отступов) */
export const HEADER_BADGE_CLASS =
  'pointer-events-none absolute right-0 top-0 z-10 flex h-3.5 min-w-3.5 translate-x-px -translate-y-px items-center justify-center rounded-full bg-[var(--color-brand)] px-0.5 text-[8px] font-bold leading-none text-white sm:h-4 sm:min-w-4 sm:text-[9px]';

/** @deprecated use HEADER_ICON_BUTTON_CLASS */
export const HEADER_ICON_BUTTON_MOBILE_CLASS = HEADER_ICON_BUTTON_CLASS;

/** Mobile-first: единый фон секций без «блоков в блоках» (откат: NEXT_PUBLIC_MOBILE_FLAT_SECTIONS=0) */
export const MOBILE_FLAT_SECTIONS =
  process.env.NEXT_PUBLIC_MOBILE_FLAT_SECTIONS !== '0';

/** Оболочка home-секций */
export const HOME_SECTION_CLASS = MOBILE_FLAT_SECTIONS
  ? 'bg-background px-4 py-10 sm:px-4 sm:py-12 lg:px-4'
  : 'bg-background px-2 py-12 sm:px-4 lg:px-4';

/** Внутренний контейнер home-секций */
export const HOME_SECTION_INNER_CLASS = MOBILE_FLAT_SECTIONS
  ? 'mx-auto w-full max-w-7xl max-md:max-w-none max-md:px-0 sm:px-6 lg:px-8'
  : 'mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8';

/** Минимальная touch-зона на mobile/tablet (< lg), сброс на desktop */
export const TOUCH_TARGET_MOBILE_CLASS =
  'min-h-[44px] min-w-[44px] touch-manipulation lg:min-h-0 lg:min-w-0';

/** Обёртка таблиц admin на узких экранах */
export const ADMIN_TABLE_SCROLL_CLASS =
  '-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0';

/** Секция с px-4: контент на всю ширину экрана на mobile */
export const MOBILE_SECTION_BLEED_CLASS =
  'max-md:-mx-4 max-md:w-[calc(100%+2rem)] max-md:max-w-none';
