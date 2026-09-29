'use client';

import { useMemo, useRef } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import type { PaginatedResponse, Product } from '@/types';
import { getProducts } from '@/lib/api/services/products.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';
import { dedupeById } from '@/lib/dedupe-by-id';
import { cn } from '@/lib/theme/utils';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS, PRODUCT_CARD_GRID_CLASS } from '@/lib/theme/spacing';

const MOBILE_IPHONE_COUNT = 3;
const MOBILE_SAMSUNG_COUNT = 1;

function ProductCardSkeleton() {
  return (
        <div className="h-full overflow-hidden rounded-[28px] border border-border bg-white">
      <div className="p-5 sm:p-6">
        <div className="relative aspect-square w-full overflow-hidden rounded-[22px] bg-zinc-100" />
      </div>
      <div className="space-y-3 px-5 pb-5 sm:px-6 sm:pb-6">
        <div className="h-4 w-5/6 rounded bg-zinc-100" />
        <div className="h-4 w-3/4 rounded bg-zinc-100" />
        <div className="h-6 w-1/2 rounded bg-zinc-100" />
      </div>
    </div>
  );
}

function pickProducts(results: Product[] | undefined, count: number): Product[] {
  return (results ?? []).slice(0, count);
}

interface TodaysProductsCarouselProps {
  initialIphone?: PaginatedResponse<Product>;
  initialAndroid?: PaginatedResponse<Product>;
}

export function TodaysProductsCarousel({
  initialIphone,
  initialAndroid,
}: TodaysProductsCarouselProps) {
  const home = useHomePageCopy();
  const sectionRef = useRef<HTMLElement>(null);
  const ringik = useRingikIntersectionTrigger(sectionRef, 'home_todays_waving_v2', {
    bubbleMs: 2000,
    visibleMs: 2800,
    threshold: 0.35,
  });

  const iphoneQuery = useQuery({
    queryKey: ['products', 'home', 'today', 'iphone'],
    queryFn: () =>
      getProducts({ category: 'iphone', page_size: 8, ordering: 'created_at', page: 1 }),
    initialData: initialIphone,
    staleTime: 60 * 1000,
  });

  const samsungQuery = useQuery({
    queryKey: ['products', 'home', 'today', 'android'],
    queryFn: () =>
      getProducts({ category: 'android', page_size: 8, ordering: 'created_at', page: 1 }),
    initialData: initialAndroid,
    staleTime: 60 * 1000,
  });

  const mobileTotal = MOBILE_IPHONE_COUNT + MOBILE_SAMSUNG_COUNT;

  const products: Product[] = useMemo(() => {
    const iphones = pickProducts(iphoneQuery.data?.results, MOBILE_IPHONE_COUNT);
    const samsung = pickProducts(samsungQuery.data?.results, MOBILE_SAMSUNG_COUNT);
    let mixed = [...iphones, ...samsung];

    if (mixed.length < mobileTotal) {
      const seen = new Set(mixed.map(p => p.id));
      const fallback = [
        ...(iphoneQuery.data?.results ?? []),
        ...(samsungQuery.data?.results ?? []),
      ].filter(p => !seen.has(p.id));
      while (mixed.length < mobileTotal && fallback.length > 0) {
        const next = fallback.shift();
        if (next) mixed.push(next);
      }
    }

    if (mixed.length === 0) return [];
    return dedupeById(mixed).slice(0, mobileTotal);
  }, [iphoneQuery.data, samsungQuery.data]);

  const isLoading = iphoneQuery.isLoading || samsungQuery.isLoading;
  const isError = iphoneQuery.isError || samsungQuery.isError;
  const error = iphoneQuery.error ?? samsungQuery.error;
  const errorText = isError ? getFriendlyErrorMessage(error) : null;

  return (
    <section ref={sectionRef} className={cn('relative', HOME_SECTION_CLASS)}>
      <div className={HOME_SECTION_INNER_CLASS}>
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
              {home.todayProducts.title}
            </h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              {home.todayProducts.subtitle}
            </p>
          </div>
          <Link
            href="/catalog"
            className="text-sm font-medium text-brand hover:underline sm:text-base"
          >
            {home.todayProducts.seeAll}
          </Link>
        </div>

        {isLoading ? (
          <div className={PRODUCT_CARD_GRID_CLASS}>
            {Array.from({ length: mobileTotal }).map((_, i) => (
              <ProductCardSkeleton key={i} />
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
                className={index === mobileTotal - 1 ? 'h-full lg:hidden' : 'h-full'}
              />
            ))}
          </div>
        )}
      </div>

      <Ringik
        pose="waving"
        placement="absolute"
        visible={ringik.visible}
        showMessage={ringik.showMessage}
        message="Листай → тут самое интересное"
        className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 scale-[1.15]"
      />
    </section>
  );
}
