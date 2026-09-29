'use client';

import { useMemo } from 'react';
import Image from 'next/image';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';
import { cn } from '@/lib/theme/utils';

import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

export interface StaffPhotoSlide {
  src: string;
  alt: string;
}

interface Props {
  slides: StaffPhotoSlide[];
  fallbackLetter?: string;
  className?: string;
}

const FRAME_CLASS =
  'relative mx-auto aspect-[4/5] w-full max-w-[280px] overflow-hidden rounded-2xl bg-zinc-100 shadow-md ring-1 ring-black/5 sm:mx-0 sm:max-w-[320px]';

function encodePublicAssetUrl(src: string): string {
  if (!src.startsWith('/')) return src;
  try {
    return src
      .split('/')
      .map((segment, index) => (index === 0 ? segment : encodeURIComponent(segment)))
      .join('/');
  } catch {
    return src;
  }
}

function StaffPhotoImage({
  slide,
  priority,
  className,
}: {
  slide: StaffPhotoSlide;
  priority?: boolean;
  className?: string;
}) {
  const src = encodePublicAssetUrl(slide.src);
  return (
    <Image
      src={src}
      alt={slide.alt}
      fill
      className={cn('object-cover', className)}
      sizes="(max-width: 640px) 280px, 320px"
      priority={priority}
      unoptimized
    />
  );
}

/** Десктоп: плавная смена второго фото при наведении */
function StaffPhotoHoverSwap({ slides }: { slides: StaffPhotoSlide[] }) {
  const [primary, secondary] = slides;

  return (
    <div
      className={cn(
        FRAME_CLASS,
        'group hidden transition-shadow duration-500 hover:shadow-xl hover:ring-[var(--color-brand)]/25 lg:block'
      )}
    >
      <StaffPhotoImage
        slide={primary}
        priority
        className="transition-[transform,opacity,filter] duration-700 ease-out group-hover:scale-[1.03] group-hover:opacity-0 group-hover:blur-[1px]"
      />
      <StaffPhotoImage
        slide={secondary}
        className="opacity-0 transition-[transform,opacity,filter] duration-700 ease-out group-hover:scale-105 group-hover:opacity-100"
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(165deg,rgba(255,255,255,0.12)_0%,transparent_45%,rgba(0,0,0,0.08)_100%)] opacity-80 transition-opacity duration-500 group-hover:opacity-100"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background:
            'radial-gradient(ellipse 80% 60% at 50% 0%, rgba(255,255,255,0.22), transparent 55%)',
        }}
        aria-hidden
      />
      <span className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-black/45 px-2.5 py-1 text-[10px] font-medium text-white/90 opacity-0 backdrop-blur-sm transition-opacity duration-500 group-hover:opacity-100">
        Наведите для другого фото
      </span>
    </div>
  );
}

/** Мобилка: свайп между фото */
function StaffPhotoMobileSwiper({ slides }: { slides: StaffPhotoSlide[] }) {
  return (
    <div className={cn('staff-photo-carousel relative w-full max-w-[280px] sm:max-w-[320px] lg:hidden', 'mx-auto sm:mx-0')}>
      <Swiper
        modules={[Navigation, Pagination]}
        navigation={{
          prevEl: '.staff-photo-prev',
          nextEl: '.staff-photo-next',
        }}
        pagination={{ clickable: true, dynamicBullets: true }}
        className={cn(FRAME_CLASS, 'mx-0 max-w-none shadow-md')}
        loop={slides.length > 1}
        spaceBetween={0}
      >
        {slides.map((slide, i) => (
          <SwiperSlide key={`${slide.src}-${i}`}>
            <div className="relative size-full">
              <StaffPhotoImage slide={slide} priority={i === 0} />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
      <button
        type="button"
        className="staff-photo-prev absolute left-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md transition hover:bg-white active:scale-95"
        aria-label="Предыдущее фото"
      >
        <ChevronLeft className="size-5" />
      </button>
      <button
        type="button"
        className="staff-photo-next absolute right-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md transition hover:bg-white active:scale-95"
        aria-label="Следующее фото"
      >
        <ChevronRight className="size-5" />
      </button>
    </div>
  );
}

export function StaffPhotoCarousel({ slides, fallbackLetter, className }: Props) {
  const hasSlides = slides.length > 0;
  const single = useMemo(() => slides.length === 1, [slides.length]);
  const multi = slides.length >= 2;

  if (!hasSlides) {
    return (
      <div className={cn(FRAME_CLASS, className)}>
        <span className="flex size-full items-center justify-center text-4xl font-bold text-foreground">
          {fallbackLetter ?? '?'}
        </span>
      </div>
    );
  }

  if (single) {
    return (
      <div className={cn(FRAME_CLASS, className)}>
        <StaffPhotoImage slide={slides[0]} priority />
      </div>
    );
  }

  return (
    <div className={cn('w-full', className)}>
      <StaffPhotoMobileSwiper slides={slides} />
      <StaffPhotoHoverSwap slides={slides} />
    </div>
  );
}
