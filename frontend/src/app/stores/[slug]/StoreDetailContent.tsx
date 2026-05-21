'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock, MapPin, Phone } from 'lucide-react';
import type { StorePage } from '@/lib/api/services/stores.service';
import { getStoreBySlug, getStoreProducts } from '@/lib/api/services/stores.service';
import { stripDescriptionHtml } from '@/lib/format-description';
import { staffProfilePath } from '@/lib/staff-path';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

const DAY_LABELS: Record<string, string> = {
  monday: 'Пн',
  tuesday: 'Вт',
  wednesday: 'Ср',
  thursday: 'Чт',
  friday: 'Пт',
  saturday: 'Сб',
  sunday: 'Вс',
};

function formatWorkingHours(working_hours: Record<string, string> | null): string {
  if (!working_hours || Object.keys(working_hours).length === 0) return '—';
  return Object.keys(working_hours)
    .filter(key => working_hours[key])
    .map(key => `${DAY_LABELS[key] ?? key}: ${working_hours[key]}`)
    .join(' · ');
}

interface Props {
  slug: string;
  initialStore: StorePage;
}

export function StoreDetailContent({ slug, initialStore }: Props) {
  const { data: store = initialStore } = useQuery({
    queryKey: ['store', 'by-slug', slug],
    queryFn: () => getStoreBySlug(slug),
    initialData: initialStore,
    staleTime: 5 * 60 * 1000,
  });

  const { data: productsPage, isLoading: productsLoading } = useQuery({
    queryKey: ['store', 'products', slug],
    queryFn: () => getStoreProducts(slug),
    staleTime: 5 * 60 * 1000,
  });

  const products = productsPage?.results ?? [];
  const catalogHref = `/catalog?store=${encodeURIComponent(slug)}`;
  const managers = store.managers ?? [];

  const images = useMemo(
    () => (store.images ?? []).filter(img => img.image),
    [store.images]
  );

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <nav className="mb-6 text-sm text-foreground-muted">
        <Link href="/stores" className="hover:text-foreground hover:underline">
          Магазины
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{store.name}</span>
      </nav>

      <h1 className="text-2xl font-semibold text-foreground md:text-3xl">{store.name}</h1>
      <p className="mt-2 flex items-start gap-2 text-foreground-muted">
        <MapPin className="mt-0.5 size-4 shrink-0" />
        {store.city}, {store.address}
      </p>
      {store.phone && (
        <p className="mt-2 flex items-center gap-2 text-sm">
          <Phone className="size-4 shrink-0" />
          <a href={`tel:${store.phone}`} className="text-info hover:underline">
            {store.phone}
          </a>
        </p>
      )}
      {store.working_hours && Object.keys(store.working_hours).length > 0 && (
        <p className="mt-2 flex items-start gap-2 text-sm text-foreground-muted">
          <Clock className="mt-0.5 size-4 shrink-0" />
          {formatWorkingHours(store.working_hours)}
        </p>
      )}

      {images.length > 0 && (
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {images.map(img => (
            <div
              key={img.id}
              className="relative aspect-[16/10] overflow-hidden rounded-2xl bg-zinc-100"
            >
              <Image
                src={img.image}
                alt={img.alt_text || store.name}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 33vw"
              />
            </div>
          ))}
        </div>
      )}

      {store.description?.trim() && (
        <p className="mt-6 whitespace-pre-wrap text-sm text-foreground-muted">
          {stripDescriptionHtml(store.description)}
        </p>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-foreground">Команда</h2>
        {managers.length === 0 ? (
          <p className="mt-2 text-sm text-foreground-muted">Менеджеры скоро появятся.</p>
        ) : (
          <div className="mt-4 -mx-1 flex gap-3 overflow-x-auto px-1 pb-2 snap-x snap-mandatory">
            {managers.map(m => (
              <Link
                key={m.id}
                href={staffProfilePath(m.slug)}
                className="flex min-w-[200px] max-w-[220px] shrink-0 snap-start items-center gap-3 rounded-2xl border border-border bg-white p-3 shadow-sm transition-colors hover:bg-zinc-50 sm:min-w-[220px]"
              >
                <div className="relative size-14 shrink-0 overflow-hidden rounded-full bg-zinc-100">
                  {m.photo ? (
                    <Image src={m.photo} alt={m.name} fill className="object-cover" sizes="56px" />
                  ) : (
                    <span className="flex size-full items-center justify-center text-lg font-semibold">
                      {m.name.slice(0, 1)}
                    </span>
                  )}
                </div>
                <div className="min-w-0">
                  <p className="truncate font-medium text-foreground">{m.name}</p>
                  <p className="truncate text-xs text-foreground-muted">
                    {m.job_title || 'Консультант'}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="mt-10">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-xl font-semibold text-foreground">В наличии в магазине</h2>
          <Button asChild variant="outline" size="sm">
            <Link href={catalogHref}>Весь каталог магазина</Link>
          </Button>
        </div>
        {productsLoading ? (
          <Loading />
        ) : products.length === 0 ? (
          <p className="text-sm text-foreground-muted">Сейчас нет товаров в наличии.</p>
        ) : (
          <div className="grid grid-cols-2 gap-5 sm:gap-6 lg:grid-cols-3 lg:gap-7">
            {products.map((product, i) => (
              <ProductCard
                key={product.id}
                product={product}
                className="h-full"
                enableTilt
                priority={i < 4}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}