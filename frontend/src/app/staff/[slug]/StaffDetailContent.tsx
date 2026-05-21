'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Star } from 'lucide-react';
import { getManagerBySlug, getManagerReviews } from '@/lib/api/services/stores.service';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import { getMediaUrl } from '@/lib/image-url';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { formatRuDateLong } from '@/lib/format-date';
import { stripDescriptionHtml } from '@/lib/format-description';
import { StaffPhotoCarousel } from '@/components/staff/StaffPhotoCarousel';
import type { ManagerManifestPhotos } from '@/lib/staff/manager-photo';
import {
  fixManagerDisplayName,
  getManagerStaticPhotoUrls,
  registerManagerStaticPhotos,
} from '@/lib/staff/manager-photo';

function StarRating({ value, max = 5 }: { value: number; max?: number }) {
  const rounded = Math.round(value * 2) / 2;
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`Рейтинг ${value}`}>
      {Array.from({ length: max }, (_, i) => {
        const filled = i + 1 <= Math.floor(rounded);
        const half = !filled && i + 0.5 === rounded;
        return (
          <Star
            key={i}
            className={`h-4 w-4 ${filled || half ? 'fill-amber-400 text-amber-400' : 'text-zinc-300'}`}
          />
        );
      })}
    </span>
  );
}

function formatReviewDate(iso: string) {
  return formatRuDateLong(iso);
}

interface Props {
  slug: string;
}

export function StaffDetailContent({ slug }: Props) {
  const {
    data: manager,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['manager', 'by-slug', slug],
    queryFn: () => getManagerBySlug(slug),
    enabled: Boolean(slug),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const { data: reviews = [], isLoading: reviewsLoading } = useQuery({
    queryKey: ['manager', 'reviews', slug],
    queryFn: () => getManagerReviews(slug),
    enabled: Boolean(slug) && Boolean(manager),
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    fetch('/menegers/manifest.json')
      .then(r => r.json())
      .then((d: { managers?: Record<string, ManagerManifestPhotos> }) => {
        if (d.managers) registerManagerStaticPhotos(d.managers);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!manager) return;
    const name = fixManagerDisplayName(manager);
    document.title = `${name} — ${manager.store?.name ?? 'Ringoo'} | Ringoo`;
  }, [manager]);

  if (!slug) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6 lg:px-8 text-center text-foreground-muted">
        Не указан адрес страницы.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="mx-auto flex max-w-3xl justify-center px-4 py-16">
        <Loading />
      </div>
    );
  }

  if (isError || !manager) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6 lg:px-8 text-center">
        <h1 className="text-xl font-semibold text-foreground">Консультант не найден</h1>
        <p className="mt-2 text-sm text-foreground-muted">
          {getFriendlyErrorMessage(error)}
        </p>
        <Button asChild className="mt-6" variant="outline">
          <Link href="/about">Вернуться к команде</Link>
        </Button>
      </div>
    );
  }

  const displayName = fixManagerDisplayName(manager);
  const avg = Number(manager.average_rating ?? 0);
  const count = Number(manager.ratings_count ?? 0);
  const storeSlug = manager.store?.slug;

  const seen = new Set<string>();
  const photoSlides: { src: string; alt: string }[] = [];
  const pushSlide = (src: string | null | undefined, alt: string) => {
    if (!src?.trim()) return;
    const resolved = src.startsWith('/') ? src : getMediaUrl(src) ?? src;
    if (seen.has(resolved)) return;
    seen.add(resolved);
    photoSlides.push({ src: resolved, alt });
  };

  for (const url of getManagerStaticPhotoUrls(manager.slug)) {
    pushSlide(url, displayName);
  }
  pushSlide(manager.photo, manager.photo_alt || displayName);
  pushSlide(manager.photo_2, manager.photo_2_alt || displayName);

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <nav className="mb-6 text-sm text-foreground-muted">
        <Link href="/about" className="hover:text-foreground hover:underline">
          О нас
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{displayName}</span>
      </nav>

      <Card className="overflow-hidden rounded-3xl border border-border bg-white p-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          <StaffPhotoCarousel
            slides={photoSlides}
            fallbackLetter={displayName.slice(0, 1)}
            className="shrink-0"
          />
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <h1 className="text-2xl font-semibold text-foreground">{displayName}</h1>
            <p className="mt-1 text-foreground-muted">
              {manager.job_title?.trim() || 'Ведущий консультант'}
            </p>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <StarRating value={avg} />
              <span className="font-semibold text-foreground">{avg.toFixed(1)}</span>
              <span className="text-sm text-foreground-muted">({count} отзывов)</span>
            </div>
            <p className="mt-3 flex items-center justify-center gap-2 text-sm text-foreground-muted sm:justify-start">
              <MapPin className="size-4 shrink-0" />
              {storeSlug ? (
                <Link href={`/stores/${encodeURIComponent(storeSlug)}`} className="text-info hover:underline">
                  {manager.store.name}
                  {manager.store.city ? `, ${manager.store.city}` : ''}
                </Link>
              ) : (
                <span>
                  {manager.store?.name}
                  {manager.store?.city ? `, ${manager.store.city}` : ''}
                </span>
              )}
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
              {storeSlug && (
                <Button asChild variant="outline" size="sm">
                  <Link href={`/catalog?store=${encodeURIComponent(storeSlug)}`}>
                    Товары в магазине
                  </Link>
                </Button>
              )}
            </div>
          </div>
        </div>

        {manager.bio?.trim() && (
          <p className="mt-6 whitespace-pre-wrap text-sm leading-relaxed text-foreground-muted">
            {stripDescriptionHtml(manager.bio)}
          </p>
        )}

      </Card>

      <section className="mt-8">
        <h2 className="text-xl font-semibold text-foreground">Отзывы</h2>
        {reviewsLoading ? (
          <div className="mt-4">
            <Loading />
          </div>
        ) : reviews.length === 0 ? (
          <p className="mt-3 text-sm text-foreground-muted">Пока нет отзывов с комментарием.</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {reviews.map(review => (
              <li key={review.id}>
                <Card className="rounded-2xl border border-border p-4">
                  <div className="flex items-center justify-between gap-2">
                    <StarRating value={review.rating} />
                    <span className="text-xs text-foreground-muted">
                      {formatReviewDate(review.created_at)}
                    </span>
                  </div>
                  {review.comment?.trim() && (
                    <p className="mt-2 text-sm text-foreground-muted">{review.comment}</p>
                  )}
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
