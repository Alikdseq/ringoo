'use client';

import Link from 'next/link';
import type { Category } from '@/types';
import { useCategories } from '@/lib/hooks/useProducts';
import { Card } from '@/components/ui/Card';
import { TYPOGRAPHY } from '@/lib/theme/typography';

/** Дефолтные категории, если API пустой (референс nextphone) */
const FALLBACK_CATEGORIES: { title: string; slug: string }[] = [
  { title: 'iPhone', slug: 'iphone' },
  { title: 'Samsung', slug: 'samsung' },
  { title: 'Huawei', slug: 'huawei' },
  { title: 'Xiaomi', slug: 'xiaomi' },
  { title: 'Realme', slug: 'realme' },
  { title: 'Tecno', slug: 'tecno' },
  { title: 'Infinix', slug: 'infinix' },
];

export function CategoriesGrid() {
  const { data: categories = [] } = useCategories();
  const list =
    categories.length > 0
      ? categories.map((c: Category) => ({ title: c.title, slug: c.slug }))
      : FALLBACK_CATEGORIES;

  return (
    <section className="border-t border-border bg-background px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className={TYPOGRAPHY.h2 + ' mb-8 text-center text-foreground'}>Каталог</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {list.map(item => (
            <Link key={item.slug} href={`/catalog?category=${item.slug}`}>
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
