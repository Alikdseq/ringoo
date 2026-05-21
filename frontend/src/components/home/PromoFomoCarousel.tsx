'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Clock } from 'lucide-react';
import type { Promotion } from '@/types';
import { getPromotions } from '@/lib/api/services/promotions.service';
import { getMediaUrl } from '@/lib/image-url';
import { usePromotionCountdown } from '@/lib/hooks/usePromotionCountdown';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';
import { cn } from '@/lib/theme/utils';

type Slide = {
  id: string;
  title: string;
  endsAt: string; // ISO
  href: string;
  image?: string | null;
  tone: 'mint' | 'sky' | 'zinc' | 'amber';
};

const TONE_CLASS: Record<Slide['tone'], string> = {
  mint: 'bg-[radial-gradient(circle_at_20%_20%,rgba(34,197,94,0.20),transparent_55%),linear-gradient(180deg,#ffffff,#f6fff8)]',
  sky: 'bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.18),transparent_55%),linear-gradient(180deg,#ffffff,#f6faff)]',
  zinc: 'bg-[radial-gradient(circle_at_20%_20%,rgba(24,24,27,0.10),transparent_55%),linear-gradient(180deg,#ffffff,#fafafa)]',
  amber: 'bg-[radial-gradient(circle_at_20%_20%,rgba(245,158,11,0.20),transparent_55%),linear-gradient(180deg,#ffffff,#fffaf1)]',
};

function pickTone(i: number): Slide['tone'] {
  return (['mint', 'sky', 'zinc', 'amber'] as const)[i % 4];
}

/** Без Date.now(): бэкенд уже отдаёт только активные акции; иначе SSR и клиент могут расходиться у границы end_date. */
function buildSlidesFromPromotions(promotions: Promotion[]): Slide[] {
  const usable = promotions
    .filter(p => Boolean(p.end_date))
    .map((p, i) => ({
      id: String(p.id),
      title: p.title?.trim() || 'Акция',
      endsAt: p.end_date,
      href: '/promotions',
      image: p.image ? getMediaUrl(p.image) : null,
      tone: pickTone(i),
    }))
    .filter(s => Number.isFinite(Date.parse(s.endsAt)));
  return usable.slice(0, 4);
}

function MockSlideTimer({ endsAt, overlay }: { endsAt: string; overlay?: boolean }) {
  const timeLeft = usePromotionCountdown(endsAt);
  return (
    <div
      className={cn(
        'rounded-2xl border px-4 py-3 backdrop-blur',
        overlay
          ? 'border-white/25 bg-black/35 text-white/90'
          : 'border-border bg-white/85 text-foreground-muted'
      )}
    >
      <div className="flex items-center gap-2 text-sm font-medium">
        <Clock className={cn('h-4 w-4', overlay ? 'text-white' : 'text-brand')} />
        <span>До конца скидки</span>
      </div>
      <div
        className={cn(
          'mt-1 text-lg font-semibold tabular-nums sm:text-xl',
          overlay ? 'text-white' : 'text-foreground'
        )}
      >
        {timeLeft === 'Завершена' ? 'Завершена' : timeLeft}
      </div>
    </div>
  );
}

function PromoFomoCarouselInner() {
  const home = useHomePageCopy();
  const { data: promotions = [] } = useQuery({
    queryKey: ['promotions', 'home-fomo'],
    queryFn: () => getPromotions({}),
    staleTime: 60 * 1000,
  });

  const slides: Slide[] = useMemo(() => {
    const fromApi = buildSlidesFromPromotions(promotions);
    if (fromApi.length > 0) return fromApi;

    return [
      {
        id: 'm1',
        title: 'Скидка 20% на смартфоны',
        endsAt: '2030-01-01T12:00:00.000Z',
        href: '/catalog?search=смартфон',
        image: null,
        tone: 'mint',
      },
      {
        id: 'm2',
        title: '−15% на наушники сегодня',
        endsAt: '2030-01-01T10:00:00.000Z',
        href: '/catalog?search=наушники',
        image: null,
        tone: 'sky',
      },
      {
        id: 'm3',
        title: 'Аксессуары по спеццене',
        endsAt: '2030-01-01T08:00:00.000Z',
        href: '/catalog?search=аксессуары',
        image: null,
        tone: 'amber',
      },
    ];
  }, [promotions]);

  const [index, setIndex] = useState(0);
  const dragXRef = useRef<number | null>(null);

  const count = slides.length;
  const safeIndex = count === 0 ? 0 : ((index % count) + count) % count;
  const current = slides[safeIndex];

  useEffect(() => {
    if (count <= 1) return;
    const t = window.setInterval(() => {
      setIndex(i => (i + 1) % count);
    }, 4000);
    return () => window.clearInterval(t);
  }, [count]);

  if (!current) return null;

  const go = (next: number) => setIndex(((next % count) + count) % count);

  const hasImage = Boolean(current.image);

  return (
    <section className="bg-background px-2 pt-6 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <h2 className="mb-3 text-2xl font-semibold tracking-tight text-foreground sm:mb-4 sm:text-3xl">
          {home.promo.sectionTitle}
        </h2>
        <Card
          className={cn(
            'relative overflow-hidden rounded-[36px] border border-border p-0',
            TONE_CLASS[current.tone]
          )}
          onPointerDown={e => {
            dragXRef.current = e.clientX;
          }}
          onPointerUp={e => {
            const start = dragXRef.current;
            dragXRef.current = null;
            const dx = start == null ? 0 : e.clientX - start;
            if (Math.abs(dx) > 40) {
              go(index + (dx < 0 ? 1 : -1));
            }
          }}
          onPointerCancel={() => {
            dragXRef.current = null;
          }}
        >
          <div className="flex flex-col">
            {/* Только этот блок: фото фоном + текст / таймер / CTA поверх */}
            <div
              className={cn(
                'relative mx-6 mt-8 min-h-[280px] overflow-hidden rounded-[28px] border border-border/70 sm:mx-10 sm:min-h-[300px] lg:mx-14 lg:min-h-[320px]',
                !hasImage && 'bg-white/55 backdrop-blur-[2px]'
              )}
            >
              {hasImage ? (
                <>
                  <Image
                    src={current.image as string}
                    alt=""
                    fill
                    sizes="(max-width: 1024px) 100vw, min(92rem, 100vw)"
                    className="object-cover"
                    loading="lazy"
                    unoptimized={(current.image as string).startsWith('http')}
                    aria-hidden
                  />
                  <div
                    className="absolute inset-0 bg-gradient-to-r from-black/78 via-black/48 to-black/15 sm:via-black/38"
                    aria-hidden
                  />
                </>
              ) : null}

              <div className="relative z-10 flex min-h-[280px] flex-col justify-center px-6 py-8 sm:min-h-[300px] sm:px-10 sm:py-10 lg:min-h-[320px] lg:px-12">
                <div className="max-w-2xl">
                  <p
                    className={cn(
                      'text-xs font-semibold uppercase tracking-wider',
                      hasImage ? 'text-white/75' : 'text-foreground-muted'
                    )}
                  >
                    {home.promo.slideEyebrow}
                  </p>
                  <h1
                    className={cn(
                      'mt-3 max-w-2xl text-3xl font-semibold leading-[1.05] tracking-tight sm:text-4xl lg:text-5xl',
                      hasImage ? 'text-white' : 'text-foreground'
                    )}
                  >
                    {current.title}
                  </h1>

                  <div className="mt-5 flex flex-wrap items-end gap-3">
                    <MockSlideTimer endsAt={current.endsAt} overlay={hasImage} />
                    <Button asChild className="w-full sm:w-auto">
                      <Link href={current.href}>Забрать скидку</Link>
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Навигация карусели — на общем фоне карточки, не на фото */}
            <div className="flex flex-col gap-4 px-6 pb-8 pt-6 sm:flex-row sm:items-center sm:justify-between sm:px-10 lg:px-14">
              <div className="flex flex-wrap items-center gap-2">
                {slides.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => go(i)}
                    className={cn(
                      'h-2.5 rounded-full transition-all',
                      i === safeIndex ? 'w-10 bg-foreground' : 'w-2.5 bg-zinc-300'
                    )}
                    aria-label={`Слайд ${i + 1} из ${count}`}
                  />
                ))}
                <span className="ml-2 text-sm tabular-nums text-foreground-muted">
                  {safeIndex + 1}/{count}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-12 w-12 rounded-full px-0"
                  onClick={() => go(index - 1)}
                  aria-label="Предыдущая акция"
                  disabled={count <= 1}
                >
                  <ChevronLeft className="h-6 w-6" />
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-12 w-12 rounded-full px-0"
                  onClick={() => go(index + 1)}
                  aria-label="Следующая акция"
                  disabled={count <= 1}
                >
                  <ChevronRight className="h-6 w-6" />
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

/** Скелетон совпадает с внешней вёрсткой карусели — без контента, зависящего от клиента/React Query. */
function PromoFomoCarouselSkeleton() {
  return (
    <section className="bg-background px-2 pt-6 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div
          className="h-[min(420px,70vw)] min-h-[320px] animate-pulse rounded-[36px] border border-border bg-muted/35 sm:min-h-[360px]"
          aria-hidden
        />
      </div>
    </section>
  );
}

/**
 * Рендер только после mount: нет рассинхрона HTML сервера и первого прохода React Query/времени.
 * (Иначе возможны warning’и при смене бандла HMR и при расхождении данных SSR/клиента.)
 */
export function PromoFomoCarousel() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <PromoFomoCarouselSkeleton />;
  return <PromoFomoCarouselInner />;
}

