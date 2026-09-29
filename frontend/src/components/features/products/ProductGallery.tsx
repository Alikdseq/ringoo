'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import type { Swiper as SwiperType } from 'swiper';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation } from 'swiper/modules';
import type { ProductDetail, ProductImage } from '@/types';
import { getMediaUrl, shouldUnoptimizeImage } from '@/lib/image-url';
import { cn } from '@/lib/theme/utils';
import { filterImagesForColorGroups, mergeColorGroups } from '@/lib/product-colors';
import {
  getCatalogImageVisualMode,
  IPHONE_COMPACT_PDP_IMAGE_IDLE_CLASS,
  IPHONE_COMPACT_PDP_IMAGE_ZOOM_CLASS,
  IPHONE_MEGA_PDP_IMAGE_IDLE_CLASS,
  IPHONE_MEGA_PDP_IMAGE_ZOOM_CLASS,
  IPHONE_TARGET_PDP_HERO_0,
  IPHONE_TARGET_PDP_HERO_1,
  isTargetIphoneGallerySlug,
} from '@/lib/product-image-boost';

import 'swiper/css';
import 'swiper/css/navigation';

interface ProductGalleryProps {
  product: ProductDetail;
  selectedGroupKey: string | null;
  /** Первый id цвета в выбранной группе (для цены и корзины на PDP) */
  onActiveColorIdChange?: (colorId: string | null) => void;
}

export function ProductGallery({
  product,
  selectedGroupKey,
  onActiveColorIdChange,
}: ProductGalleryProps) {
  const mainRef = useRef<SwiperType | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isZoomed, setIsZoomed] = useState(false);
  const galleryModules = useMemo(() => [Navigation], []);

  const allImages = product.images ?? [];
  const colorGroups = useMemo(
    () => mergeColorGroups(product.colors ?? []),
    [product.colors]
  );
  const targetIphoneGallery = isTargetIphoneGallerySlug(
    product.slug,
    product.category?.slug
  );
  const imageVisualMode = useMemo(
    () => getCatalogImageVisualMode(product.slug, product.category?.slug),
    [product.slug, product.category?.slug]
  );
  const imageMegaLayout = imageVisualMode === 'iphone-mega-cover';
  const imageCompactLayout = imageVisualMode === 'iphone-compact-contain';

  const selectedIdSet = useMemo(() => {
    if (!selectedGroupKey || !colorGroups.length) return null;
    const g = colorGroups.find(x => x.key === selectedGroupKey);
    return g ? new Set(g.colorIds) : null;
  }, [colorGroups, selectedGroupKey]);

  const images = useMemo(() => {
    if (!colorGroups.length || !selectedIdSet) {
      return allImages;
    }
    return filterImagesForColorGroups(allImages, selectedIdSet) as ProductImage[];
  }, [allImages, colorGroups.length, selectedIdSet]);

  const showGalleryNav = images.length > 1;

  const swiperDataKey = useMemo(
    () => `${product.id}:${selectedGroupKey ?? ''}:${images.map(i => i.id).join(',')}`,
    [product.id, selectedGroupKey, images]
  );

  useEffect(() => {
    setActiveIndex(0);
    setIsZoomed(false);
    queueMicrotask(() => {
      mainRef.current?.slideTo(0, 0);
    });
  }, [swiperDataKey]);

  useEffect(() => {
    if (!onActiveColorIdChange) return;
    if (!selectedGroupKey || !colorGroups.length) {
      onActiveColorIdChange(null);
      return;
    }
    const group = colorGroups.find(g => g.key === selectedGroupKey);
    onActiveColorIdChange(group?.colorIds[0] ?? null);
  }, [selectedGroupKey, colorGroups, onActiveColorIdChange]);

  const goToSlide = useCallback((index: number) => {
    mainRef.current?.slideTo(index);
    setActiveIndex(index);
  }, []);

  if (allImages.length === 0) {
    return (
      <div className="flex aspect-square w-full items-center justify-center rounded-2xl bg-white text-zinc-400 ring-1 ring-border dark:bg-zinc-950 dark:text-zinc-500">
        Нет фото
      </div>
    );
  }

  return (
    <div className="min-w-0 max-w-full space-y-3">
      <div className="grid gap-3 lg:grid-cols-[84px_minmax(0,1fr)] lg:items-stretch">
        <div
          className="order-2 flex max-h-[520px] flex-row gap-2 overflow-x-auto pb-1 lg:order-1 lg:w-[84px] lg:flex-col lg:overflow-y-auto lg:overflow-x-visible lg:pb-0"
          role="tablist"
          aria-label="Миниатюры галереи"
        >
          {images.map((img, i) => {
            const src = getMediaUrl(img.image);
            const selected = i === activeIndex;
            return (
              <button
                key={img.id}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => goToSlide(i)}
                className={cn(
                  'relative h-11 w-11 shrink-0 overflow-hidden rounded-2xl border-2 bg-white transition-colors touch-manipulation sm:h-[72px] sm:w-[72px]',
                  selected
                    ? 'border-brand ring-1 ring-brand/30'
                    : 'border-transparent hover:border-zinc-300 dark:bg-zinc-900 dark:hover:border-zinc-600'
                )}
              >
                <Image
                  src={src}
                  alt={img.alt_text ?? `${product.title}, миниатюра ${i + 1}`}
                  fill
                  sizes="84px"
                  className="object-contain p-0.5"
                  loading={i < 6 ? 'eager' : 'lazy'}
                  unoptimized={shouldUnoptimizeImage(src)}
                />
              </button>
            );
          })}
        </div>

        <div
          className={cn(
            'order-1 relative aspect-square w-full min-h-0 max-w-full overflow-hidden rounded-3xl lg:order-2',
            targetIphoneGallery ? 'bg-white' : 'bg-white dark:bg-zinc-900'
          )}
          onClick={() => setIsZoomed(z => !z)}
        >
          <div className="absolute inset-0 min-h-0">
            <Swiper
              key={`main-${swiperDataKey}`}
              modules={showGalleryNav ? galleryModules : []}
              navigation={
                showGalleryNav ? { enabled: true, hideOnClick: false } : false
              }
              allowTouchMove
              touchStartPreventDefault={false}
              resistanceRatio={0.85}
              className="h-full w-full touch-pan-y !p-0 max-md:[&_.swiper-button-next]:!hidden max-md:[&_.swiper-button-prev]:!hidden md:[&_.swiper-button-next]:!flex md:[&_.swiper-button-prev]:!flex [&_.swiper-button-next]:right-2 [&_.swiper-button-prev]:left-2 [&_.swiper-button-next]:z-[5] [&_.swiper-button-prev]:z-[5] [&_.swiper-button-next]:!size-10 [&_.swiper-button-prev]:!size-10 [&_.swiper-button-next]:!bg-transparent [&_.swiper-button-prev]:!bg-transparent [&_.swiper-button-next]:!shadow-none [&_.swiper-button-prev]:!shadow-none [&_.swiper-button-next]:text-brand [&_.swiper-button-prev]:text-brand [&_.swiper-button-next]:after:!text-lg [&_.swiper-button-prev]:after:!text-lg [&_.swiper-slide]:box-border [&_.swiper-slide]:!flex [&_.swiper-slide]:!h-full [&_.swiper-wrapper]:!h-full"
              onSwiper={instance => {
                mainRef.current = instance;
              }}
              onSlideChange={swiper => {
                setActiveIndex(swiper.activeIndex);
              }}
            >
              {images.map((img, slideIndex) => {
                const src = getMediaUrl(img.image);
                const targetHeroClass =
                  targetIphoneGallery && slideIndex < 2
                    ? slideIndex === 0
                      ? IPHONE_TARGET_PDP_HERO_0
                      : IPHONE_TARGET_PDP_HERO_1
                    : null;
                return (
                  <SwiperSlide key={img.id} className="!h-full min-h-0">
                    <div
                      className={cn(
                        'flex h-full min-h-0 w-full cursor-zoom-in items-center justify-center',
                        imageMegaLayout ? 'p-0' : 'p-1 sm:p-2 md:p-3'
                      )}
                    >
                      <div
                        className={cn(
                          'relative h-full w-full max-h-full lg:min-h-0',
                          imageMegaLayout
                            ? 'min-h-0 sm:min-h-0'
                            : 'min-h-[min(78vw,480px)] sm:min-h-[min(62vw,560px)]'
                        )}
                      >
                        <Image
                          src={src}
                          alt={img.alt_text ?? product.title}
                          fill
                          sizes="(max-width: 640px) 92vw, (max-width: 1024px) 55vw, min(720px, 48vw)"
                          quality={90}
                          className={cn(
                            'transition-transform duration-200',
                            targetHeroClass ??
                              (isZoomed
                                ? imageMegaLayout
                                  ? IPHONE_MEGA_PDP_IMAGE_ZOOM_CLASS
                                  : imageCompactLayout
                                    ? IPHONE_COMPACT_PDP_IMAGE_ZOOM_CLASS
                                    : 'object-contain object-center scale-110'
                                : imageMegaLayout
                                  ? IPHONE_MEGA_PDP_IMAGE_IDLE_CLASS
                                  : imageCompactLayout
                                    ? IPHONE_COMPACT_PDP_IMAGE_IDLE_CLASS
                                    : 'object-contain object-center scale-100')
                          )}
                          priority={slideIndex === 0}
                          loading={slideIndex === 0 ? 'eager' : 'lazy'}
                          unoptimized={shouldUnoptimizeImage(src)}
                        />
                      </div>
                    </div>
                  </SwiperSlide>
                );
              })}
            </Swiper>
          </div>
        </div>
      </div>
    </div>
  );
}
