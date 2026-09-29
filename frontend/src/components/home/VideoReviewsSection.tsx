'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft, ChevronRight, Pause, Play, Volume2, VolumeX } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { cn } from '@/lib/theme/utils';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS } from '@/lib/theme/spacing';

type VideoReview = {
  id: string;
  name: string;
  city: string;
  quote: string;
  /** URL на видео (mp4/webm). Можно положить файлы в /frontend/public/otzivi/... */
  src?: string | null;
};

const REVIEW_VIDEO_1 = '/otzivi/отзыв1.MP4';

const MOCK_VIDEO_REVIEWS: VideoReview[] = [
  {
    id: 'vr-1',
    name: 'Покупатель',
    city: 'Ringoo',
    quote: 'Реальный отзыв из магазина — смотрите видео.',
    src: REVIEW_VIDEO_1,
  },
  { id: 'vr-2', name: 'Диана', city: 'Беслан', quote: 'Взяла в рассрочку — оформили за минуты.', src: null },
  { id: 'vr-3', name: 'Тимур', city: 'Моздок', quote: 'Товар как новый, всё честно.', src: null },
  { id: 'vr-4', name: 'Зарина', city: 'Владикавказ', quote: 'Забрала в магазине в тот же день.', src: null },
  { id: 'vr-5', name: 'Руслан', city: 'Беслан', quote: 'Рекомендую Ringoo.', src: null },
];

/**
 * Кириллица в публичных URL → percent-encode каждый сегмент пути.
 * Без этого iOS Safari может не загрузить видео.
 */
function encodePublicAssetUrl(src: string): string {
  if (!src.startsWith('/')) return src;
  return src
    .split('/')
    .map((segment, index) => (index === 0 ? segment : encodeURIComponent(segment)))
    .join('/');
}

interface VideoCardProps {
  item: VideoReview & { src: string | null };
  /** Полная высота для reels (mobile) */
  reelMode?: boolean;
  isPlaying: boolean;
  isMuted: boolean;
  onPlayingChange: (playing: boolean) => void;
  onMutedChange: (muted: boolean) => void;
  registerRef: (id: string, el: HTMLVideoElement | null) => void;
}

function VideoCard({
  item,
  reelMode,
  isPlaying,
  isMuted,
  onPlayingChange,
  onMutedChange,
  registerRef,
}: VideoCardProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hasVideo = Boolean(item.src);

  const handleRef = useCallback(
    (el: HTMLVideoElement | null) => {
      videoRef.current = el;
      registerRef(item.id, el);
    },
    [item.id, registerRef]
  );

  const togglePlay = useCallback(() => {
    const el = videoRef.current;
    if (!el || !hasVideo) return;
    if (el.paused) {
      const p = el.play();
      if (p && typeof p.then === 'function') {
        p.then(() => onPlayingChange(true)).catch(() => onPlayingChange(false));
      } else {
        onPlayingChange(true);
      }
    } else {
      el.pause();
      onPlayingChange(false);
    }
  }, [hasVideo, onPlayingChange]);

  const toggleMute = useCallback(
    (e: React.MouseEvent | React.PointerEvent) => {
      e.stopPropagation();
      const el = videoRef.current;
      if (!el) return;
      el.muted = !el.muted;
      onMutedChange(el.muted);
    },
    [onMutedChange]
  );

  return (
    <Card
      className={cn(
        'shrink-0 overflow-hidden rounded-[28px] border border-border bg-white p-0',
        reelMode ? 'snap-start w-full' : 'w-[280px]'
      )}
      data-reel-item={reelMode ? 'true' : undefined}
      data-reel-id={reelMode ? item.id : undefined}
    >
      <div
        className={cn(
          'relative w-full bg-zinc-100',
          reelMode ? 'h-[calc(100dvh-220px)]' : 'aspect-[9/16]'
        )}
      >
        {hasVideo && item.src ? (
          <video
            ref={handleRef}
            src={item.src}
            className="h-full w-full object-cover"
            playsInline
            {...({ 'webkit-playsinline': '', 'x5-playsinline': '' } as Record<string, string>)}
            preload="none"
            muted={isMuted}
            loop
            controls={false}
            controlsList="nodownload noplaybackrate"
            disablePictureInPicture
            onPlay={() => onPlayingChange(true)}
            onPause={() => onPlayingChange(false)}
            onEnded={() => onPlayingChange(false)}
            onClick={togglePlay}
          />
        ) : (
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(34,197,94,0.20),transparent_45%),linear-gradient(180deg,#fafafa,#f4f4f5)]" />
        )}

        {/* Прозрачный layer для тапа */}
        <button
          type="button"
          onClick={togglePlay}
          className={cn(
            'absolute inset-0 flex items-center justify-center',
            hasVideo ? 'cursor-pointer' : 'cursor-default'
          )}
          aria-label={hasVideo ? (isPlaying ? 'Пауза' : 'Воспроизвести видео') : 'Видео скоро'}
        >
          <span
            className={cn(
              'inline-flex h-14 w-14 items-center justify-center rounded-full',
              'bg-white/90 shadow-sm backdrop-blur transition-opacity',
              hasVideo ? (isPlaying ? 'opacity-0 group-hover/video:opacity-100' : 'opacity-100') : 'opacity-75'
            )}
          >
            {isPlaying ? (
              <Pause className="h-6 w-6 text-foreground" />
            ) : (
              <Play className="h-6 w-6 text-foreground" />
            )}
          </span>
        </button>

        {hasVideo && (
          <button
            type="button"
            onClick={toggleMute}
            className="absolute right-3 top-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-black/55 text-white shadow-sm backdrop-blur transition-colors hover:bg-black/70"
            aria-label={isMuted ? 'Включить звук' : 'Выключить звук'}
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        )}

        {!hasVideo && (
          <span className="absolute left-4 top-4 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">
            Скоро
          </span>
        )}

        {reelMode && (
          <>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-36 bg-gradient-to-t from-black/60 to-transparent" />
            <div className="pointer-events-none absolute bottom-0 left-0 right-0 p-5 text-white">
              <p className="text-sm font-semibold">
                {item.name} <span className="text-white/80">· {item.city}</span>
              </p>
              <p className="mt-1 text-sm text-white/85">{item.quote}</p>
            </div>
          </>
        )}
      </div>

      {!reelMode && (
        <div className="space-y-1 px-6 py-5">
          <p className="text-sm font-semibold text-foreground">
            {item.name} <span className="text-foreground-muted">· {item.city}</span>
          </p>
          <p className="text-sm text-foreground-muted line-clamp-2">{item.quote}</p>
        </div>
      )}
    </Card>
  );
}

export function VideoReviewsSection() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [mutedMap, setMutedMap] = useState<Record<string, boolean>>({});

  const items = useMemo(
    () =>
      MOCK_VIDEO_REVIEWS.map(item => ({
        ...item,
        src: item.src ? encodePublicAssetUrl(item.src) : null,
      })),
    []
  );

  const registerRef = useCallback((id: string, el: HTMLVideoElement | null) => {
    videoRefs.current[id] = el;
  }, []);

  /** Только одно видео играет одновременно. */
  useEffect(() => {
    Object.entries(videoRefs.current).forEach(([id, el]) => {
      if (!el || id === playingId) return;
      if (!el.paused) {
        try {
          el.pause();
        } catch {
          /* ignore */
        }
      }
    });
  }, [playingId]);

  const setIsPlaying = useCallback(
    (id: string) => (playing: boolean) => {
      setPlayingId(prev => {
        if (playing) return id;
        if (!playing && prev === id) return null;
        return prev;
      });
    },
    []
  );

  const setIsMuted = useCallback(
    (id: string) => (muted: boolean) => {
      setMutedMap(prev => ({ ...prev, [id]: muted }));
    },
    []
  );

  const scroll = (dir: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const step = 320;
    scrollRef.current.scrollBy({ left: dir === 'left' ? -step : step, behavior: 'smooth' });
  };

  return (
    <section className={HOME_SECTION_CLASS}>
      <div className={HOME_SECTION_INNER_CLASS}>
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

        {/* Mobile reels: вертикальный свайп */}
        <div
          className={cn(
            'sm:hidden',
            'h-[calc(100dvh-220px)] overflow-y-auto pr-1',
            'snap-y snap-mandatory',
            '[-webkit-overflow-scrolling:touch] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
          )}
          aria-label="Видеоотзывы (Reels)"
        >
          <div className="space-y-4">
            {items.map(item => (
              <div key={item.id} className="group/video">
                <VideoCard
                  item={item}
                  reelMode
                  isPlaying={playingId === item.id}
                  isMuted={mutedMap[item.id] ?? true}
                  onPlayingChange={setIsPlaying(item.id)}
                  onMutedChange={setIsMuted(item.id)}
                  registerRef={registerRef}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Desktop carousel: горизонтальный */}
        <div
          ref={scrollRef}
          className="hidden gap-5 overflow-x-auto scroll-smooth pb-3 [-webkit-overflow-scrolling:touch] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:flex"
          aria-label="Видеоотзывы"
        >
          {items.map(item => (
            <div key={item.id} className="group/video">
              <VideoCard
                item={item}
                isPlaying={playingId === item.id}
                isMuted={mutedMap[item.id] ?? true}
                onPlayingChange={setIsPlaying(item.id)}
                onMutedChange={setIsMuted(item.id)}
                registerRef={registerRef}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
