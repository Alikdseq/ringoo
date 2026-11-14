/**
 * B8-016 / Fix I: единый список публичных статических маршрутов для
 * `sitemap.ts` (XML) и `site-map/page.tsx` (HTML-карта).
 *
 * Не включать: auth, profile, cart/checkout, orders/payment, admin, wishlist.
 * Динамика (товары/категории/магазины/статьи) — только в XML через API.
 */

export type PublicSiteRoute = {
  path: string;
  label: string;
  /** Приоритет в XML sitemap (опционально). */
  priority?: number;
  changeFrequency?: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never';
};

/** Статические публичные страницы, пригодные для индексации. */
export const PUBLIC_INDEXABLE_STATIC_ROUTES: readonly PublicSiteRoute[] = [
  { path: '/', label: 'Главная', priority: 1, changeFrequency: 'daily' },
  { path: '/catalog', label: 'Каталог', priority: 0.9, changeFrequency: 'daily' },
  { path: '/promotions', label: 'Акции', priority: 0.8, changeFrequency: 'weekly' },
  { path: '/installment', label: 'Рассрочка', priority: 0.7, changeFrequency: 'monthly' },
  { path: '/stores', label: 'Магазины', priority: 0.8, changeFrequency: 'weekly' },
  { path: '/about', label: 'О нас', priority: 0.7, changeFrequency: 'monthly' },
  { path: '/blog', label: 'Блог', priority: 0.75, changeFrequency: 'weekly' },
  { path: '/news', label: 'Новости', priority: 0.75, changeFrequency: 'weekly' },
  { path: '/order-status', label: 'Проверить заказ', priority: 0.5, changeFrequency: 'monthly' },
  { path: '/site-map', label: 'Карта сайта', priority: 0.4, changeFrequency: 'monthly' },
  { path: '/docs/requisites', label: 'Реквизиты организации', priority: 0.5, changeFrequency: 'yearly' },
  { path: '/docs/offer', label: 'Публичная оферта', priority: 0.5, changeFrequency: 'yearly' },
  { path: '/docs/privacy', label: 'Политика конфиденциальности', priority: 0.5, changeFrequency: 'yearly' },
  { path: '/docs/consent', label: 'Согласие на обработку ПДн', priority: 0.4, changeFrequency: 'yearly' },
  { path: '/docs/marketing-consent', label: 'Согласие на маркетинг', priority: 0.4, changeFrequency: 'yearly' },
  { path: '/docs/cookies', label: 'Cookie и аналитика', priority: 0.4, changeFrequency: 'yearly' },
] as const;

/** Пути, которые нельзя индексировать и нельзя класть в sitemap / HTML-карту. */
export const NON_INDEXABLE_PATH_PREFIXES = [
  '/admin',
  '/api',
  '/cart',
  '/checkout',
  '/wishlist',
  '/orders',
  '/order-rate',
  '/profile',
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
] as const;

export function isNonIndexablePath(pathname: string): boolean {
  const p = pathname.split('?')[0] || pathname;
  return NON_INDEXABLE_PATH_PREFIXES.some(
    prefix => p === prefix || p.startsWith(`${prefix}/`)
  );
}
