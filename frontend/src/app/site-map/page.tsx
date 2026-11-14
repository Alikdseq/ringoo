import Link from 'next/link';
import { PUBLIC_INDEXABLE_STATIC_ROUTES } from '@/lib/seo/public-site-routes';

/**
 * Человекочитаемая карта публичных разделов.
 * Список совпадает со статикой XML (`app/sitemap.ts` → `PUBLIC_INDEXABLE_STATIC_ROUTES`).
 * Товары/категории/магазины/статьи — в `/sitemap.xml` (динамическая выборка API).
 */
export default function SiteMapPage() {
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-2xl font-semibold text-foreground">Карта сайта</h1>
      <p className="mb-6 text-sm text-foreground-muted">
        Публичные разделы сайта. Корзина, оформление заказа, личный кабинет и админка в карту не
        входят. Полный машинный список URL (включая товары и категории) —{' '}
        <a href="/sitemap.xml" className="text-brand underline hover:no-underline">
          sitemap.xml
        </a>
        .
      </p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {PUBLIC_INDEXABLE_STATIC_ROUTES.map(item => (
          <li key={item.path}>
            <Link
              href={item.path}
              className="block rounded-lg border border-border px-3 py-2 text-sm text-foreground hover:bg-zinc-50"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
