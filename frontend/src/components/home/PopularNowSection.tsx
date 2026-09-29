'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { useQueries } from '@tanstack/react-query';
import type { PaginatedResponse, Product } from '@/types';
import { getProducts, type ProductFilters } from '@/lib/api/services/products.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Button } from '@/components/ui/Button';
import { dedupeById } from '@/lib/dedupe-by-id';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS, PRODUCT_CARD_GRID_CLASS } from '@/lib/theme/spacing';

const NEWEST_FILTERS: ProductFilters = {
  page_size: 3,
  page: 1,
  ordering: 'created_at',
};

interface PopularNowSectionProps {
  initialSamsung?: PaginatedResponse<Product>;
  initialIphone?: PaginatedResponse<Product>;
}

export function PopularNowSection({ initialSamsung, initialIphone }: PopularNowSectionProps) {
  const results = useQueries({
    queries: [
      {
        queryKey: ['products', 'home', 'popular-now', 'samsung', NEWEST_FILTERS],
        queryFn: () => getProducts({ ...NEWEST_FILTERS, category: 'samsung' }),
        initialData: initialSamsung,
        staleTime: 60 * 1000,
      },
      {
        queryKey: ['products', 'home', 'popular-now', 'iphone', NEWEST_FILTERS],
        queryFn: () => getProducts({ ...NEWEST_FILTERS, category: 'iphone' }),
        initialData: initialIphone,
        staleTime: 60 * 1000,
      },
    ],
  });

  const [samsungQ, iphoneQ] = results;

  const products = useMemo(() => {
    const s = samsungQ.data?.results ?? [];
    const i = iphoneQ.data?.results ?? [];
    const out: Product[] = [];
    for (let k = 0; k < 3; k++) {
      if (s[k]) out.push(s[k]!);
      if (i[k]) out.push(i[k]!);
    }
    return dedupeById(out);
  }, [samsungQ.data, iphoneQ.data]);

  const isLoading = results.some(r => r.isPending);
  const error = results.find(r => r.isError)?.error;
  const errorText = error ? getFriendlyErrorMessage(error) : null;

  return (
    <section className={HOME_SECTION_CLASS}>
      <div className={HOME_SECTION_INNER_CLASS}>
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Популярное сейчас</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Три новых Samsung и три новых iPhone.
            </p>
          </div>
          <Link href="/catalog" className="text-sm font-medium text-brand hover:underline sm:text-base">
            Смотреть всё
          </Link>
        </div>

        {isLoading ? (
          <div className={PRODUCT_CARD_GRID_CLASS}>
            {Array.from({ length: 6 }).map((_, idx) => (
              <div
                key={idx}
                className="h-[360px] animate-pulse rounded-[28px] border border-border bg-white"
              />
            ))}
          </div>
        ) : errorText ? (
          <div className="rounded-2xl border border-border bg-white p-6 text-sm text-foreground-muted">
            {errorText}
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white p-6 text-sm text-foreground-muted">
            Сейчас нет товаров для отображения.
          </div>
        ) : (
          <div className={PRODUCT_CARD_GRID_CLASS}>
            {products.map((product, index) => (
              <ProductCard
                key={product.id}
                product={product}
                enableTilt
                className="h-full"
              />
            ))}
          </div>
        )}

        <div className="mt-8 flex justify-center">
          <Button asChild type="button" variant="secondary">
            <Link href="/catalog">Больше в каталоге</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
