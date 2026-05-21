'use client';

import Image from 'next/image';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';
import type { PageGalleryImage } from '@/lib/api/services/pageGallery.service';
import { getMediaUrl, shouldUnoptimizeImage } from '@/lib/image-url';

import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

interface Props {
  images: PageGalleryImage[];
  className?: string;
}

export function PageHeroGallery({ images, className }: Props) {
  const slides = images
    .map(img => {
      const src = getMediaUrl(img.image) ?? img.image;
      return {
        id: img.id,
        src,
        alt: img.alt_text || 'Ringoo',
        unoptimized: src.startsWith('/magazins/') || shouldUnoptimizeImage(src),
      };
    })
    .filter(s => s.src);

  if (slides.length === 0) {
    return (
      <div
        className={`relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden rounded-3xl bg-zinc-100 ring-1 ring-black/5 ${className ?? ''}`}
      >
        <span className="text-sm text-foreground-muted">Фото скоро появятся</span>
      </div>
    );
  }

  if (slides.length === 1) {
    return (
      <div
        className={`relative aspect-[4/3] w-full overflow-hidden rounded-3xl bg-zinc-100 ring-1 ring-black/5 ${className ?? ''}`}
      >
        <Image
          src={slides[0]!.src}
          alt={slides[0]!.alt}
          fill
          unoptimized={slides[0]!.unoptimized}
          className="object-cover"
          sizes="(max-width: 1024px) 100vw, 50vw"
        />
      </div>
    );
  }

  return (
    <div
      className={`page-hero-gallery relative aspect-[4/3] w-full overflow-hidden rounded-3xl bg-zinc-100 ring-1 ring-black/5 ${className ?? ''}`}
    >
      <Swiper
        modules={[Navigation, Pagination]}
        navigation={{
          prevEl: '.page-hero-gallery-prev',
          nextEl: '.page-hero-gallery-next',
        }}
        pagination={{ clickable: true }}
        loop={slides.length > 2}
        className="h-full w-full"
      >
        {slides.map((slide, index) => (
          <SwiperSlide key={`${slide.id}-${index}`}>
            <div className="relative h-full min-h-[200px] w-full">
              <Image
                src={slide.src}
                alt={slide.alt}
                fill
                unoptimized={slide.unoptimized}
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 50vw"
              />
            </div>
          </SwiperSlide>
        ))}
      </Swiper>
      <button
        type="button"
        className="page-hero-gallery-prev absolute left-3 top-1/2 z-10 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md hover:bg-white"
        aria-label="Назад"
      >
        <ChevronLeft className="size-5" />
      </button>
      <button
        type="button"
        className="page-hero-gallery-next absolute right-3 top-1/2 z-10 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 shadow-md hover:bg-white"
        aria-label="Вперёд"
      >
        <ChevronRight className="size-5" />
      </button>
    </div>
  );
}
