'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import type { ProductDetail } from '@/types';
import { getProducts } from '@/lib/api/services/products.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { ProductCard } from '@/components/features/products/ProductCard';
import {
  readRecentlyViewedProducts,
  recentSnapshotToProduct,
  type RecentProductSnapshot,
} from '@/lib/recently-viewed-products';

const SIMILAR_PAGE_SIZE = 16;
const SIMILAR_SHOW = 4;
const RECENT_SHOW = 8;

interface ProductDetailRecommendationsProps {
  product: ProductDetail;
}

export function ProductDetailRecommendations({ product }: ProductDetailRecommendationsProps) {
  const categorySlug = product.category?.slug ?? '';

  const { data: similarPage, isLoading: similarLoading, isError: similarError, error: similarErr } =
    useQuery({
      queryKey: ['products', 'similar', categorySlug, product.id],
      queryFn: () =>
        getProducts({
          category: categorySlug,
          page_size: SIMILAR_PAGE_SIZE,
          ordering: 'popular',
          page: 1,
        }),
      enabled: Boolean(categorySlug),
      staleTime: 5 * 60 * 1000,
    });

  const similarProducts = useMemo(() => {
    if (!similarPage?.results) return [];
    return similarPage.results.filter(p => p.id !== product.id).slice(0, SIMILAR_SHOW);
  }, [similarPage, product.id]);

  const [recentSnapshots, setRecentSnapshots] = useState<RecentProductSnapshot[]>([]);

  useEffect(() => {
    const load = () =>
      readRecentlyViewedProducts()
        .filter(s => s.id !== product.id)
        .slice(0, RECENT_SHOW);
    setRecentSnapshots(load());
    const onUpdate = () => setRecentSnapshots(load());
    window.addEventListener('ringoo-recent-products', onUpdate);
    return () => window.removeEventListener('ringoo-recent-products', onUpdate);
  }, [product.id]);

  const similarErrorText = similarError ? getFriendlyErrorMessage(similarErr) : null;

  return (
    <>
      <section className="rounded-2xl border border-border bg-card p-5 sm:p-6">
        <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground sm:text-xl">Похожие товары</h2>
            <p className="mt-1 text-sm text-foreground-muted">
              В той же категории — чтобы сравнить и выбрать удобнее.
            </p>
          </div>
          {categorySlug ? (
            <Link
              href={`/catalog?category=${encodeURIComponent(categorySlug)}`}
              className="shrink-0 text-sm font-medium text-brand hover:underline"
            >
              Вся категория
            </Link>
          ) : null}
        </div>

        {!categorySlug ? (
          <p className="text-sm text-foreground-muted">Категория не указана — подборку показать нельзя.</p>
        ) : similarLoading ? (
          <div className="grid grid-cols-2 gap-5 sm:gap-6 lg:grid-cols-3 lg:gap-7">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-[360px] animate-pulse rounded-[28px] border border-border bg-white"
              />
            ))}
          </div>
        ) : similarErrorText ? (
          <p className="text-sm text-foreground-muted">{similarErrorText}</p>
        ) : similarProducts.length === 0 ? (
          <p className="text-sm text-foreground-muted">
            Пока нет других товаров в этой категории. Загляните в общий каталог.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-5 sm:gap-6 lg:grid-cols-3 lg:gap-7">
            {similarProducts.map((p, index) => (
              <ProductCard
                key={p.id}
                product={p}
                priority={index === 0}
                enableTilt
                className="h-full"
              />
            ))}
          </div>
        )}
      </section>

      {recentSnapshots.length > 0 ? (
        <section className="rounded-2xl border border-border bg-card p-5 sm:p-6">
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-foreground sm:text-xl">
                Вы смотрели ранее
              </h2>
              <p className="mt-1 text-sm text-foreground-muted">
                Недавние просмотры с этого устройства — можно быстро вернуться к интересным позициям.
              </p>
            </div>
            <Link href="/catalog" className="shrink-0 text-sm font-medium text-brand hover:underline">
              В каталог
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 sm:gap-6 lg:grid-cols-3 lg:gap-7">
            {recentSnapshots.map((s, index) => (
              <ProductCard
                key={s.id}
                product={recentSnapshotToProduct(s)}
                priority={index === 0}
                enableTilt
                className="h-full"
              />
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
