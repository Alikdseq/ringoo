'use client';

import { useMemo } from 'react';
import Image from 'next/image';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';

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

export function StaffPhotoCarousel({ slides, fallbackLetter, className }: Props) {
  const hasSlides = slides.length > 0;

  const single = useMemo(() => slides.length === 1, [slides.length]);

  if (!hasSlides) {
    return (
      <div
        className={`relative mx-auto aspect-[4/5] w-full max-w-[280px] overflow-hidden rounded-2xl bg-zinc-100 sm:mx-0 sm:max-w-[320px] ${className ?? ''}`}
      >
        <span className="flex size-full items-center justify-center text-4xl font-bold text-foreground">
          {fallbackLetter ?? '?'}
        </span>
      </div>
    );
  }

  if (single) {
    const slide = slides[0];
    return (
      <div
        className={`relative mx-auto aspect-[4/5] w-full max-w-[280px] overflow-hidden rounded-2xl bg-zinc-100 sm:mx-0 sm:max-w-[320px] ${className ?? ''}`}
      >
        <Image
          src={slide.src}
          alt={slide.alt}
          fill
          className="object-cover"
          sizes="320px"
          priority
          unoptimized={slide.src.startsWith('http://')}
        />
      </div>
    );
  }

  return (
    <div
      className={`staff-photo-carousel relative mx-auto w-full max-w-[280px] sm:mx-0 sm:max-w-[320px] ${className ?? ''}`}
    >
      <Swiper
        modules={[Navigation, Pagination]}
        navigation={{
          prevEl: '.staff-photo-prev',
          nextEl: '.staff-photo-next',
        }}
        pagination={{ clickable: true }}
        className="aspect-[4/5] overflow-hidden rounded-2xl bg-zinc-100"
        loop
      >
        {slides.map((slide, i) => (
          <SwiperSlide key={`${slide.src}-${i}`}>
            <div className="relative size-full">
              <Image
                src={slide.src}
                alt={slide.alt}
                fill
                className="object-cover"
                sizes="320px"
                priority={i === 0}
                unoptimized={slide.src.startsWith('http://')}
              />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
      <button
        type="button"
        className="staff-photo-prev absolute left-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md transition hover:bg-white"
        aria-label="Предыдущее фото"
      >
        <ChevronLeft className="size-5" />
      </button>
      <button
        type="button"
        className="staff-photo-next absolute right-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md transition hover:bg-white"
        aria-label="Следующее фото"
      >
        <ChevronRight className="size-5" />
      </button>
    </div>
  );
}
