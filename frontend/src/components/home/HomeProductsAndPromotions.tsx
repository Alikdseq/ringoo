'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { Clock } from 'lucide-react';
import type { Product } from '@/types';
import type { Promotion } from '@/types';
import { getProducts } from '@/lib/api/services/products.service';
import { getPromotions } from '@/lib/api/services/promotions.service';
import { stripDescriptionHtml } from '@/lib/format-description';
import { getMediaUrl } from '@/lib/image-url';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { cn } from '@/lib/theme/utils';
import { usePromotionCountdown } from '@/lib/hooks/usePromotionCountdown';
import { PRODUCT_CARD_GRID_CLASS } from '@/lib/theme/spacing';

const HOME_PRODUCTS_LIMIT = 8;
const HOME_PROMOTIONS_LIMIT = 4;

function formatDiscount(promotion: Promotion): string {
  if (promotion.discount_type === 'percent') {
    return `−${Number(promotion.discount_value)}%`;
  }
  return `−${promotion.discount_value} ${CURRENCY_SYMBOL}`;
}

function HomePromotionCard({ promotion }: { promotion: Promotion }) {
  const timeLeft = usePromotionCountdown(promotion.end_date);
  const imageSrc = promotion.image ? getMediaUrl(promotion.image) : null;

  return (
    <Link href="/promotions">
      <Card className="flex h-full flex-col overflow-hidden p-0 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
        <div className="relative aspect-[2/1] w-full shrink-0 bg-zinc-100">
          {imageSrc ? (
            <Image
              src={imageSrc}
              alt=""
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
              className="object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-foreground-subtle">
              Нет изображения
            </div>
          )}
          <div className="absolute left-2 top-2 rounded bg-brand px-2 py-1 text-xs font-medium text-white">
            {formatDiscount(promotion)}
          </div>
        </div>
        <div className="flex flex-1 flex-col p-3">
          <h2 className="mb-2 font-semibold text-foreground">{promotion.title}</h2>
          {promotion.description && (
            <p className="mb-3 line-clamp-2 flex-1 text-sm text-foreground-muted">
              {stripDescriptionHtml(promotion.description)}
            </p>
          )}
          <div
            className={cn(
              'flex items-center gap-1.5 text-sm',
              timeLeft === 'Завершена' ? 'text-danger' : 'text-foreground-muted'
            )}
          >
            <Clock className="h-4 w-4 shrink-0" />
            <span>{timeLeft === 'Завершена' ? 'Акция завершена' : `До конца: ${timeLeft}`}</span>
          </div>
        </div>
      </Card>
    </Link>
  );
}

export function HomeProductsAndPromotions() {
  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products', 'home', { page_size: HOME_PRODUCTS_LIMIT, ordering: 'rating_desc' }],
    queryFn: () =>
      getProducts({ page_size: HOME_PRODUCTS_LIMIT, ordering: 'rating_desc', page: 1 }),
  });
  const { data: promotions = [], isLoading: promotionsLoading } = useQuery({
    queryKey: ['promotions', 'home'],
    queryFn: () => getPromotions({}),
  });

  const products: Product[] = productsData?.results ?? [];
  const promotionsSlice = promotions.slice(0, HOME_PROMOTIONS_LIMIT);

  return (
    <section className="mx-auto grid w-full max-w-6xl gap-10 px-4 py-8">
      {/* Популярные товары */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Популярные товары</h2>
          <Link href="/catalog" className="text-sm font-medium text-brand hover:underline">
            Смотреть всё
          </Link>
        </div>
        {productsLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white p-8 text-center text-foreground-muted">
            Сейчас нет товаров для отображения.
          </div>
        ) : (
          <div className={PRODUCT_CARD_GRID_CLASS}>
            {products.map((product, index) => (
              <ProductCard key={product.id} product={product} priority={index === 0} />
            ))}
          </div>
        )}
      </div>

      {/* Акции и спецпредложения */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-foreground">Акции и спецпредложения</h2>
          <Link href="/promotions" className="text-sm font-medium text-brand hover:underline">
            Все акции
          </Link>
        </div>
        {promotionsLoading ? (
          <div className="flex min-h-[180px] items-center justify-center">
            <Loading />
          </div>
        ) : promotionsSlice.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white p-6 text-center text-sm text-foreground-muted">
            Сейчас нет активных акций.
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {promotionsSlice.map(promotion => (
              <HomePromotionCard key={promotion.id} promotion={promotion} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
