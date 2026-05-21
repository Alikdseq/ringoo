import Link from 'next/link';

const LINKS = [
  { href: '/', label: 'Главная' },
  { href: '/catalog', label: 'Каталог' },
  { href: '/promotions', label: 'Акции' },
  { href: '/stores', label: 'Магазины' },
  { href: '/blog', label: 'Блог' },
  { href: '/news', label: 'Новости' },
  { href: '/order-status', label: 'Проверить заказ' },
  { href: '/cart', label: 'Корзина' },
  { href: '/checkout', label: 'Оформление заказа' },
  { href: '/docs/requisites', label: 'Реквизиты организации' },
  { href: '/docs/offer', label: 'Оферта' },
  { href: '/docs/privacy', label: 'Политика конфиденциальности' },
];

/** Человекочитаемая карта разделов. Машинный sitemap — `/sitemap.xml` (см. `app/sitemap.ts`). */
export default function SiteMapPage() {
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-2xl font-semibold text-foreground">Карта сайта</h1>
      <p className="mb-6 text-sm text-foreground-muted">
        Базовая структура всех разделов фронтенда. Для поисковых систем используйте{' '}
        <a href="/sitemap.xml" className="text-brand underline hover:no-underline">
          sitemap.xml
        </a>
        .
      </p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {LINKS.map(item => (
          <li key={item.href}>
            <Link
              href={item.href}
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
