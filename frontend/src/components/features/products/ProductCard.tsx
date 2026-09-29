'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { ShoppingCart, Star, Heart } from 'lucide-react';
import type { Product } from '@/types';
import { Card } from '@/components/ui/Card';
import { Card3DTilt } from '@/components/ui/Card3DTilt';
import { Button } from '@/components/ui/Button';
import { DiscountBadge } from '@/components/ui/Badge';
import { getMediaUrl, shouldUnoptimizeImage } from '@/lib/image-url';
import { BLUR_DATA_URL } from '@/lib/performance/blur-placeholders';
import { useCartFly } from '@/lib/providers/CartFlyProvider';
import { useAddToCart } from '@/lib/hooks/useCart';
import { useAuth } from '@/lib/hooks/useAuth';
import { useWishlist } from '@/lib/hooks/useWishlist';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { addToCartAriaLabel } from '@/lib/ui-mode/copy';
import { cn } from '@/lib/theme/utils';
import {
  filterImagesForColorGroups,
  mergeColorGroups,
  mergeListColorsForCard,
  resolveColorSwatchHex,
} from '@/lib/product-colors';
import { catalogCardImageClassName } from '@/lib/product-image-boost';
import { resolveProductDisplayPrice } from '@/lib/product-pricing';
import { dedupeById } from '@/lib/dedupe-by-id';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';

import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

interface ProductCardProps {
  product: Product;
  className?: string;
  /** Для первого видимого изображения на главной — улучшает LCP */
  priority?: boolean;
  /** Включить 3D tilt эффект на desktop */
  enableTilt?: boolean;
  /** Swiper-галерея на карточке (в каталоге отключено — меньше JS) */
  galleryMode?: boolean;
}

export function ProductCard({
  product,
  className,
  priority,
  enableTilt,
  galleryMode = true,
}: ProductCardProps) {
  const { mode } = useUiMode();
  const pathname = usePathname();
  const cardSwiperModules = useMemo(
    () => [Navigation, Pagination],
    []
  );
  const listColors = useMemo(
    () => mergeListColorsForCard(product.colors ?? []),
    [product.colors, product.id]
  );
  const colorGroups = useMemo(
    () => mergeColorGroups(product.colors ?? []),
    [product.colors, product.id]
  );
  const [selectedColorId, setSelectedColorId] = useState<string | null>(
    () => listColors[0]?.id ?? null
  );
  const [colorsOpen, setColorsOpen] = useState(false);

  useEffect(() => {
    setColorsOpen(false);
  }, [product.id]);

  useEffect(() => {
    if (!listColors.length) {
      setSelectedColorId(null);
      return;
    }
    setSelectedColorId(prev => {
      if (prev && listColors.some(c => c.id === prev)) return prev;
      return listColors[0]!.id;
    });
  }, [product.id, listColors]);

  const activeListColor = listColors.find(c => c.id === selectedColorId) ?? listColors[0];
  const displayPrice = useMemo(
    () => resolveProductDisplayPrice(product, selectedColorId),
    [product, selectedColorId]
  );
  const hasDiscount = displayPrice.discount_percent > 0;
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const addButtonRef = useRef<HTMLButtonElement>(null);
  const cartFly = useCartFly();
  const addToCartMutation = useAddToCart();
  const { isAuthenticated } = useAuth();
  const { isInWishlist, add, remove } = useWishlist({
    enabled: isAuthenticated,
  });
  const inWishlist = isInWishlist(product.id);
  const cardImageClass = useMemo(
    () => catalogCardImageClassName(product.slug, product.category?.slug),
    [product.slug, product.category?.slug]
  );

  const productHref = `/products/${product.slug}`;

  type CardSlide = { id: string; src: string; alt: string };

  const cardSlides = useMemo((): CardSlide[] => {
    const title = product.title;
    const imgs = [...(product.images ?? [])].sort((a, b) => {
      if (a.is_main && !b.is_main) return -1;
      if (!a.is_main && b.is_main) return 1;
      return (a.sort_order ?? 0) - (b.sort_order ?? 0);
    });

    const toSlides = (images: typeof imgs): CardSlide[] =>
      images.map(img => ({
        id: img.id,
        src: getMediaUrl(img.image),
        alt: img.alt_text ?? title,
      }));

    // Нет вариантов цвета на карточке — показываем общую галерею как раньше
    if (!listColors.length) {
      if (imgs.length > 1) return toSlides(imgs);
      if (imgs.length === 1) return toSlides(imgs);
      return [];
    }

    const selectedGroup =
      colorGroups.find(g => g.colorIds.includes(selectedColorId ?? '')) ?? colorGroups[0]!;
    const idSet = new Set(selectedGroup.colorIds);
    const forColor = filterImagesForColorGroups(imgs, idSet);
    if (forColor.length > 0) {
      return toSlides(forColor);
    }

    if (activeListColor?.preview_image) {
      return [
        {
          id: `pv-${activeListColor.id}`,
          src: getMediaUrl(activeListColor.preview_image),
          alt: activeListColor.preview_alt ?? activeListColor.label ?? title,
        },
      ];
    }

    const neutrals = imgs.filter(img => !img.color);
    if (neutrals.length > 0) {
      return toSlides(neutrals);
    }

    if (imgs[0]) {
      return toSlides([imgs[0]]);
    }

    return [];
  }, [
    product.images,
    product.id,
    product.title,
    listColors,
    colorGroups,
    selectedColorId,
    activeListColor,
  ]);

  const uniqueCardSlides = useMemo(() => dedupeById(cardSlides), [cardSlides]);
  const galleryKey = `${product.id}:${selectedColorId ?? ''}:${uniqueCardSlides.map(s => s.id).join(',')}`;
  const displaySlides = galleryMode ? uniqueCardSlides : uniqueCardSlides.slice(0, 1);
  const showGalleryNav = displaySlides.length > 1;
  const swiperLoop = displaySlides.length > 2;

  const handleWishlistToggle = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isAuthenticated) {
      window.location.href = `/login?next=${encodeURIComponent(pathname ?? '/catalog')}`;
      return;
    }
    if (inWishlist) remove(product.id);
    else add(product.id);
  };

  const handleAddToCart = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setAddError(null);
    addToCartMutation.mutate(
      {
        productId: product.id,
        quantity: 1,
        colorId: selectedColorId ?? undefined,
      },
      {
        onSuccess: () => {
          const rect = addButtonRef.current?.getBoundingClientRect();
          if (rect && cartFly?.triggerFly) {
            cartFly.triggerFly(rect);
          }
          setIsAdding(true);
          window.setTimeout(() => setIsAdding(false), 400);
        },
        onError: (err: Error) => {
          const message =
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
            'Не удалось добавить в корзину';
          setAddError(message);
          setTimeout(() => setAddError(null), 3000);
        },
      }
    );
  };

  return (
    <Card3DTilt disableTilt={!enableTilt}>
      <Card
        variant="interactive"
        className={cn(
          'flex h-full flex-col overflow-hidden p-0',
          'rounded-2xl border border-border bg-white md:rounded-[28px]',
          className
        )}
      >
        <div className="relative">
            <div className="relative aspect-square w-full touch-pan-y overflow-hidden rounded-[28px] bg-white overscroll-x-contain">
              {displaySlides.length > 1 ? (
                <Swiper
                  key={galleryKey}
                  modules={showGalleryNav ? cardSwiperModules : [Pagination]}
                  navigation={
                    showGalleryNav
                      ? { enabled: true, hideOnClick: false }
                      : false
                  }
                  pagination={{ clickable: true, dynamicBullets: true }}
                  loop={swiperLoop}
                  slidesPerView={1}
                  spaceBetween={0}
                  touchStartPreventDefault={false}
                  preventClicksPropagation
                  className="product-card-swiper relative z-0 h-full w-full max-md:[&_.swiper-button-next]:!hidden max-md:[&_.swiper-button-prev]:!hidden md:[&_.swiper-button-next]:!flex md:[&_.swiper-button-prev]:!flex [&_.swiper-button-next]:right-1 [&_.swiper-button-prev]:left-1 [&_.swiper-button-next]:z-[5] [&_.swiper-button-prev]:z-[5] [&_.swiper-button-next]:!size-8 [&_.swiper-button-prev]:!size-8 [&_.swiper-button-next]:!bg-transparent [&_.swiper-button-prev]:!bg-transparent [&_.swiper-button-next]:!shadow-none [&_.swiper-button-prev]:!shadow-none [&_.swiper-button-next]:text-brand [&_.swiper-button-prev]:text-brand [&_.swiper-button-next]:after:!text-base [&_.swiper-button-prev]:after:!text-base [&_.swiper-pagination]:bottom-2 [&_.swiper-pagination-bullet]:bg-zinc-400 [&_.swiper-pagination-bullet-active]:bg-brand"
                >
                  {displaySlides.map((slide, si) => (
                    <SwiperSlide key={`${product.id}-${si}-${slide.id}`} className="!h-full">
                      <Link
                        href={productHref}
                        className="relative block h-full w-full"
                        draggable={false}
                      >
                        <span className="relative block aspect-square w-full">
                          <Image
                            src={slide.src}
                            alt={slide.alt}
                            fill
                            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 50vw, 34vw"
                            className={cardImageClass}
                            loading={si === 0 && priority ? 'eager' : 'lazy'}
                            priority={Boolean(si === 0 && priority)}
                            placeholder={si === 0 && priority ? 'blur' : 'empty'}
                            blurDataURL={si === 0 && priority ? BLUR_DATA_URL : undefined}
                            unoptimized={shouldUnoptimizeImage(slide.src)}
                          />
                        </span>
                      </Link>
                    </SwiperSlide>
                  ))}
                </Swiper>
              ) : displaySlides.length === 1 ? (
                <Link
                  key={galleryKey}
                  href={productHref}
                  className="relative block h-full w-full"
                  draggable={false}
                >
                  <span className="relative block aspect-square w-full">
                    <Image
                      src={displaySlides[0]!.src}
                      alt={displaySlides[0]!.alt}
                      fill
                      sizes="(max-width: 640px) 50vw, (max-width: 1024px) 50vw, 34vw"
                      className={cardImageClass}
                      loading={priority ? 'eager' : 'lazy'}
                      priority={priority}
                      placeholder={priority ? 'blur' : 'empty'}
                      blurDataURL={priority ? BLUR_DATA_URL : undefined}
                      unoptimized={shouldUnoptimizeImage(displaySlides[0]!.src)}
                    />
                  </span>
                </Link>
              ) : (
                <div className="flex h-full items-center justify-center text-foreground-subtle">
                  Нет фото
                </div>
              )}
              {hasDiscount && <DiscountBadge percent={displayPrice.discount_percent} />}
            </div>

          </div>

        <Link href={productHref} className="flex flex-1 flex-col">
            <div
              className="space-y-2 px-4 pt-3 md:px-6"
              onClick={e => e.preventDefault()}
              onKeyDown={e => e.stopPropagation()}
              role="presentation"
            >
              {listColors.length === 1 ? (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-foreground-muted">Цвет:</span>
                  {listColors.map(c => {
                    const fill = resolveColorSwatchHex(c);
                    return (
                      <span
                        key={c.id}
                        className="flex items-center gap-1.5 rounded-full border border-brand bg-brand/5 py-0.5 pl-0.5 pr-2 text-xs text-foreground"
                        title={c.label}
                      >
                        <span
                          className="h-6 w-6 shrink-0 rounded-full border-2 border-white shadow ring-1 ring-black/10"
                          style={{ backgroundColor: fill }}
                          aria-hidden
                        />
                        <span className="max-w-[9rem] truncate">{c.label}</span>
                      </span>
                    );
                  })}
                </div>
              ) : (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={e => {
                        e.preventDefault();
                        e.stopPropagation();
                        setColorsOpen(o => !o);
                      }}
                      className={cn(
                        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                        colorsOpen
                          ? 'border-brand bg-brand/5 text-foreground'
                          : 'border-border bg-zinc-50 text-foreground-muted hover:border-zinc-300'
                      )}
                      aria-expanded={colorsOpen}
                    >
                      Цвета
                    </button>
                    {!colorsOpen && activeListColor ? (
                      <span className="flex min-w-0 items-center gap-1.5 text-xs text-foreground-muted">
                        <span
                          className="h-5 w-5 shrink-0 rounded-full border-2 border-white shadow ring-1 ring-black/10"
                          style={{
                            backgroundColor: resolveColorSwatchHex(activeListColor),
                          }}
                          aria-hidden
                        />
                        <span className="truncate">{activeListColor.label}</span>
                      </span>
                    ) : null}
                  </div>
                  {colorsOpen ? (
                    <div className="flex flex-wrap gap-2">
                      {listColors.map(c => {
                        const active = c.id === (selectedColorId ?? listColors[0]?.id);
                        const fill = resolveColorSwatchHex(c);
                        return (
                          <button
                            key={c.id}
                            type="button"
                            title={c.label}
                            aria-label={c.label}
                            aria-pressed={active}
                            onClick={e => {
                              e.preventDefault();
                              e.stopPropagation();
                              setSelectedColorId(c.id);
                            }}
                            className={cn(
                              'flex items-center gap-1.5 rounded-full border py-0.5 pl-0.5 pr-2 text-left text-xs transition-colors',
                              active
                                ? 'border-brand bg-brand/5 text-foreground'
                                : 'border-transparent bg-zinc-50 text-foreground-muted hover:border-zinc-200'
                            )}
                          >
                            <span
                              className="h-6 w-6 shrink-0 rounded-full border-2 border-white shadow ring-1 ring-black/10"
                              style={{ backgroundColor: fill }}
                              aria-hidden
                            />
                            <span className="max-w-[8rem] truncate sm:max-w-[10rem]">{c.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </>
              )}
            </div>

          <div className="flex flex-1 flex-col px-6 pb-6 pt-5">
            <div className="flex items-start justify-between gap-3">
              <h3 className="line-clamp-2 min-w-0 flex-1 text-[17px] font-semibold leading-snug text-foreground sm:text-[18px]">
                {product.title}
              </h3>
              <motion.div className="hidden shrink-0 flex-row-reverse items-center gap-2 md:flex">
                <button
                  type="button"
                  onClick={handleWishlistToggle}
                  className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-white shadow-sm transition-colors hover:bg-zinc-50"
                  aria-label={inWishlist ? 'Удалить из избранного' : 'Добавить в избранное'}
                >
                  <Heart
                    className={cn(
                      'h-6 w-6',
                      inWishlist ? 'fill-red-500 text-red-500' : 'text-zinc-500'
                    )}
                  />
                </button>
                <motion.div
                  animate={isAdding ? { scale: [1, 0.92, 1.06, 1] } : { scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <Button
                    ref={addButtonRef}
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-11 w-11 rounded-full px-0"
                    onClick={handleAddToCart}
                    disabled={addToCartMutation.isPending}
                    aria-label={addToCartAriaLabel(mode)}
                  >
                    <ShoppingCart className="h-8 w-8 stroke-[3]" />
                  </Button>
                </motion.div>
              </motion.div>
            </div>
            <div className="mt-3 flex items-start justify-between gap-3">
              <div className="flex min-w-0 flex-wrap items-baseline gap-2">
              <span className="text-[19px] font-semibold text-foreground sm:text-[20px]">
                {Math.round(Number(displayPrice.price))} {CURRENCY_SYMBOL}
              </span>
              {displayPrice.old_price && (
                <span className="text-sm text-foreground-muted line-through">
                  {Math.round(Number(displayPrice.old_price))} {CURRENCY_SYMBOL}
                </span>
              )}
              </div>
              <div className="flex shrink-0 flex-col gap-2 md:hidden">
                <motion.div
                  animate={isAdding ? { scale: [1, 0.92, 1.06, 1] } : { scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="h-11 w-11 rounded-full px-0"
                    onClick={handleAddToCart}
                    disabled={addToCartMutation.isPending}
                    aria-label={addToCartAriaLabel(mode)}
                  >
                    <ShoppingCart className="h-8 w-8 stroke-[3]" />
                  </Button>
                </motion.div>
                <button
                  type="button"
                  onClick={handleWishlistToggle}
                  className="flex h-11 w-11 items-center justify-center rounded-full border border-border bg-white shadow-sm transition-colors hover:bg-zinc-50"
                  aria-label={inWishlist ? 'Удалить из избранного' : 'Добавить в избранное'}
                >
                  <Heart
                    className={cn(
                      'h-6 w-6',
                      inWishlist ? 'fill-red-500 text-red-500' : 'text-zinc-500'
                    )}
                  />
                </button>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between gap-2 text-sm">
              <span className="flex items-center gap-1">
                <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
                <span className="text-foreground-muted">
                  {product.rating.toFixed(1)}{' '}
                  <span className="text-foreground-subtle">({product.reviews_count})</span>
                </span>
              </span>
              {typeof product.available_quantity_total === 'number' ? (
                <span
                  className={cn(
                    'text-sm',
                    product.available_quantity_total > 0 ? 'text-brand' : 'text-foreground-muted'
                  )}
                >
                  {product.available_quantity_total > 0
                    ? `В наличии: ${product.available_quantity_total}`
                    : 'Нет в наличии'}
                </span>
              ) : null}
            </div>

            {addError && <p className="mt-2 text-xs text-danger">{addError}</p>}
          </div>
        </Link>
      </Card>
    </Card3DTilt>
  );
}
