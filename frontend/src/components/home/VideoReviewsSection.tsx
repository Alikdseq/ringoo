'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight, Play } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/theme/utils';

type VideoReview = {
  id: string;
  name: string;
  city: string;
  quote: string;
  /** URL на видео (mp4/webm). Можно положить файлы в /frontend/public/videos/... */
  src?: string | null;
};

// Заглушки — подключим реальные видео позже (public/videos/*.mp4)
const MOCK_VIDEO_REVIEWS: VideoReview[] = [
  { id: 'vr-1', name: 'Аслан', city: 'Владикавказ', quote: 'Быстро, удобно, доволен.', src: null },
  { id: 'vr-2', name: 'Диана', city: 'Беслан', quote: 'Взяла в рассрочку — оформили за минуты.', src: null },
  { id: 'vr-3', name: 'Тимур', city: 'Моздок', quote: 'Товар как новый, всё честно.', src: null },
  { id: 'vr-4', name: 'Зарина', city: 'Владикавказ', quote: 'Забрала в магазине в тот же день.', src: null },
  { id: 'vr-5', name: 'Руслан', city: 'Беслан', quote: 'Рекомендую Ringoo.', src: null },
];

export function VideoReviewsSection() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const reelRef = useRef<HTMLDivElement>(null);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const [activeId, setActiveId] = useState<string | null>(null);

  const items = useMemo(() => MOCK_VIDEO_REVIEWS, []);

  const scroll = (dir: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const step = 320;
    scrollRef.current.scrollBy({ left: dir === 'left' ? -step : step, behavior: 'smooth' });
  };

  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([id, el]) => {
      if (!el) return;
      if (id !== activeId) {
        try {
          el.pause();
          el.currentTime = 0;
        } catch {
          /* ignore */
        }
      }
    });
  }, [activeId]);

  useEffect(() => {
    const root = reelRef.current;
    if (!root) return;
    const cards = Array.from(root.querySelectorAll<HTMLElement>('[data-reel-item="true"]'));
    if (cards.length === 0) return;

    const observer = new IntersectionObserver(
      entries => {
        const best = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => (b.intersectionRatio ?? 0) - (a.intersectionRatio ?? 0))[0];
        const id = best?.target?.getAttribute('data-reel-id') ?? null;
        if (id) setActiveId(id);
      },
      { root, threshold: [0.6, 0.75, 0.9] }
    );

    cards.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <section className="bg-background px-2 py-12 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Отзывы</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Коротко. По делу. Реальные люди — реальная техника.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/stores" className="text-sm font-medium text-brand hover:underline sm:text-base">
              Смотреть все
            </Link>
            <div className="hidden items-center gap-1 sm:flex">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-10 w-10 rounded-full px-0"
                onClick={() => scroll('left')}
                aria-label="Назад"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-10 w-10 rounded-full px-0"
                onClick={() => scroll('right')}
                aria-label="Вперёд"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile reels: swipe up/down */}
        <div
          ref={reelRef}
          className={cn(
            'sm:hidden',
            'h-[calc(100dvh-220px)] overflow-y-auto pr-1',
            'snap-y snap-mandatory',
            '[-webkit-overflow-scrolling:touch] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
          )}
          aria-label="Видеоотзывы (Reels)"
        >
          <div className="space-y-4">
            {items.map(item => {
              const isActive = activeId === item.id;
              const hasVideo = Boolean(item.src);
              return (
                <Card
                  key={item.id}
                  data-reel-item="true"
                  data-reel-id={item.id}
                  className="snap-start overflow-hidden rounded-[28px] border border-border bg-white p-0"
                >
                  <div className="relative h-[calc(100dvh-220px)] w-full bg-zinc-100">
                    {hasVideo ? (
                      <video
                        ref={el => {
                          videoRefs.current[item.id] = el;
                        }}
                        src={item.src ?? undefined}
                        className="h-full w-full object-cover"
                        playsInline
                        muted
                        controls={isActive}
                        preload="metadata"
                      />
                    ) : (
                      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,197,94,0.20),transparent_45%),linear-gradient(180deg,#fafafa,#f4f4f5)]" />
                    )}

                    <button
                      type="button"
                      onClick={() => {
                        if (!hasVideo) return;
                        setActiveId(item.id);
                        const el = videoRefs.current[item.id];
                        if (el) void el.play();
                      }}
                      className={cn(
                        'absolute inset-0 flex items-center justify-center',
                        hasVideo ? 'cursor-pointer' : 'cursor-default'
                      )}
                      aria-label={hasVideo ? 'Воспроизвести видео' : 'Видео скоро'}
                    >
                      <span
                        className={cn(
                          'inline-flex h-14 w-14 items-center justify-center rounded-full',
                          'bg-white/90 shadow-sm backdrop-blur',
                          hasVideo ? 'opacity-100' : 'opacity-75'
                        )}
                      >
                        <Play className="h-6 w-6 text-foreground" />
                      </span>
                    </button>

                    {!hasVideo && (
                      <span className="absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">
                        Скоро
                      </span>
                    )}

                    <div className="pointer-events-none absolute inset-x-0 bottom-0 h-36 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-0 left-0 right-0 p-5 text-white">
                      <p className="text-sm font-semibold">
                        {item.name} <span className="text-white/80">· {item.city}</span>
                      </p>
                      <p className="mt-1 text-sm text-white/85">{item.quote}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Desktop carousel: horizontal */}
        <div
          ref={scrollRef}
          className="hidden gap-5 overflow-x-auto scroll-smooth pb-3 [-webkit-overflow-scrolling:touch] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:flex"
          aria-label="Видеоотзывы"
        >
          {items.map(item => {
            const isActive = activeId === item.id;
            const hasVideo = Boolean(item.src);
            return (
              <Card
                key={item.id}
                className={cn(
                  'shrink-0 overflow-hidden rounded-[28px] border border-border bg-white p-0',
                  'w-[280px]'
                )}
              >
                <div className="relative aspect-[9/16] w-full bg-zinc-100">
                  {hasVideo ? (
                    <video
                      ref={el => {
                        videoRefs.current[item.id] = el;
                      }}
                      src={item.src ?? undefined}
                      className="h-full w-full object-cover"
                      playsInline
                      muted
                      controls={isActive}
                      preload="metadata"
                    />
                  ) : (
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,197,94,0.20),transparent_45%),linear-gradient(180deg,#fafafa,#f4f4f5)]" />
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      if (!hasVideo) return;
                      setActiveId(item.id);
                      const el = videoRefs.current[item.id];
                      if (el) void el.play();
                    }}
                    className={cn(
                      'absolute inset-0 flex items-center justify-center',
                      hasVideo ? 'cursor-pointer' : 'cursor-default'
                    )}
                    aria-label={hasVideo ? 'Воспроизвести видео' : 'Видео скоро'}
                  >
                    <span
                      className={cn(
                        'inline-flex h-14 w-14 items-center justify-center rounded-full',
                        'bg-white/90 shadow-sm backdrop-blur',
                        hasVideo ? 'opacity-100' : 'opacity-75'
                      )}
                    >
                      <Play className="h-6 w-6 text-foreground" />
                    </span>
                  </button>

                  {!hasVideo && (
                    <span className="absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">
                      Скоро
                    </span>
                  )}
                </div>

                <div className="space-y-1 px-6 py-5">
                  <p className="text-sm font-semibold text-foreground">
                    {item.name} <span className="text-foreground-muted">· {item.city}</span>
                  </p>
                  <p className="text-sm text-foreground-muted line-clamp-2">{item.quote}</p>
                </div>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}

