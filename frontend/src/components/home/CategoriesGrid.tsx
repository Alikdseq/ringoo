'use client';

import Link from 'next/link';
import { LINK_PREFETCH_DEFAULT } from '@/lib/navigation/link-prefetch';
import type { Category } from '@/types';
import { useCategories } from '@/lib/hooks/useProducts';
import { Card } from '@/components/ui/Card';
import { TYPOGRAPHY } from '@/lib/theme/typography';

/** Запасной список, если API пустой */
const FALLBACK_CATEGORIES: { title: string; slug: string }[] = [
  { title: 'Каталог', slug: 'catalog' },
];

function pickMainSections(categories: Category[]): Category[] {
  const mains = categories
    .filter(c => c.is_catalog_main)
    .sort(
      (a, b) =>
        (a.catalog_main_sort ?? 0) - (b.catalog_main_sort ?? 0) ||
        a.title.localeCompare(b.title, 'ru')
    );
  if (mains.length > 0) return mains;
  // Пока флаги не проставлены — только корни 1С (parent=null), не всё дерево.
  return categories.filter(c => !c.parent);
}

export function CategoriesGrid() {
  const { data: categories = [] } = useCategories();
  const mains = pickMainSections(categories);
  const list =
    mains.length > 0
      ? mains.map(c => ({ title: c.title, slug: c.slug }))
      : FALLBACK_CATEGORIES;

  return (
    <section className="border-t border-border bg-background px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className={TYPOGRAPHY.h2 + ' mb-8 text-center text-foreground'}>Каталог</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {list.map(item => (
            <Link
              key={item.slug}
              href={
                item.slug === 'catalog' ? '/catalog' : `/catalog/category/${encodeURIComponent(item.slug)}`
              }
              prefetch={LINK_PREFETCH_DEFAULT}
            >
              <Card className="flex aspect-square flex-col items-center justify-center p-4 transition-all duration-200 hover:-translate-y-1 hover:shadow-md">
                <div className="mb-2 h-16 w-16 rounded-xl bg-zinc-100" />
                <span className={TYPOGRAPHY.bodySmall + ' text-center font-medium text-foreground'}>
                  {item.title}
                </span>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
