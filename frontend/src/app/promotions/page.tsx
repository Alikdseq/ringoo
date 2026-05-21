'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { Clock, Copy, Share2, Users } from 'lucide-react';
import type { Promotion } from '@/types';
import { getPromotions } from '@/lib/api/services/promotions.service';
import { stripDescriptionHtml } from '@/lib/format-description';
import { getMediaUrl } from '@/lib/image-url';
import { usePromotionCountdown } from '@/lib/hooks/usePromotionCountdown';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { cn } from '@/lib/theme/utils';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { SubscribeDealsSection } from '@/components/home/SubscribeDealsSection';
import { InstallmentZeroSection } from '@/components/home/InstallmentZeroSection';
import { getProducts } from '@/lib/api/services/products.service';
import type { Product } from '@/types';
import { ProductCard } from '@/components/features/products/ProductCard';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/navigation';

type PromoKind = 'all' | 'discount' | 'installment' | 'gift' | 'product_of_day';

function formatDiscount(promotion: Promotion): string {
  if (promotion.discount_type === 'percent') return `−${Number(promotion.discount_value)}%`;
  return `−${promotion.discount_value} ${CURRENCY_SYMBOL}`;
}

function toUtmCatalogHref(p: Promotion) {
  const base = '/catalog';
  const q = new URLSearchParams();
  if (p.category_slugs?.[0]) q.set('category', p.category_slugs[0]);
  q.set('utm_source', 'promotions');
  q.set('utm_medium', 'card');
  q.set('utm_campaign', String(p.id));
  return `${base}?${q.toString()}`;
}

function guessKind(p: Promotion): Exclude<PromoKind, 'all'> {
  const t = `${p.title ?? ''} ${p.description ?? ''}`.toLowerCase();
  if (t.includes('товар дня')) return 'product_of_day';
  if (t.includes('расср') || t.includes('0%')) return 'installment';
  if (t.includes('подар')) return 'gift';
  return 'discount';
}

function PromoImageArea({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'relative flex w-full items-center justify-center overflow-visible bg-white p-4',
        'aspect-[4/3] sm:aspect-[3/2] lg:aspect-[16/11] lg:min-h-[300px]',
        className
      )}
    >
      {children}
    </div>
  );
}

function PromoBadge({ kind, text }: { kind: Exclude<PromoKind, 'all'>; text: string }) {
  const tone =
    kind === 'installment'
      ? 'bg-emerald-600'
      : kind === 'gift'
        ? 'bg-sky-600'
        : kind === 'product_of_day'
          ? 'bg-amber-600'
          : 'bg-zinc-900';
  return (
    <span className={cn('inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold text-white', tone)}>
      {text}
    </span>
  );
}

function ShareButton({ promotion }: { promotion: Promotion }) {
  const shareUrl = typeof window === 'undefined' ? '' : window.location.href;
  const title = promotion.title ?? 'Акция';

  const onShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ title, url: shareUrl });
        return;
      }
      await navigator.clipboard.writeText(shareUrl);
    } catch {
      // ignore
    }
  };

  return (
    <Button type="button" variant="secondary" size="sm" onClick={onShare} className="gap-2">
      <Share2 className="h-4 w-4" />
      Поделиться
    </Button>
  );
}

function CopyLinkButton() {
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      // ignore
    }
  };
  return (
    <Button type="button" variant="secondary" size="sm" onClick={onCopy} className="gap-2">
      <Copy className="h-4 w-4" />
      Ссылка
    </Button>
  );
}

function PromoCard({ promotion }: { promotion: Promotion }) {
  const timeLeft = usePromotionCountdown(promotion.end_date);
  const imageSrc = promotion.image ? getMediaUrl(promotion.image) : null;
  const kind = guessKind(promotion);
  const ended = timeLeft === 'Завершена';
  const badgeText =
    kind === 'installment'
      ? '0%'
      : kind === 'gift'
        ? 'Подарок'
        : kind === 'product_of_day'
          ? 'Товар дня'
          : formatDiscount(promotion);

  // пока нет поля участников — делаем мягкое соцдоказательство детерминированно
  const participants = useMemo(() => {
    const seed = String(promotion.id).split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    return 900 + (seed % 2400);
  }, [promotion.id]);

  return (
    <Card className="overflow-hidden p-0">
      <div className="relative bg-white">
        <PromoImageArea>
          {imageSrc ? (
            <Image
              src={imageSrc}
              alt=""
              width={800}
              height={600}
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              className="max-h-full max-w-full object-contain object-center"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-foreground-subtle">
              Акция
            </div>
          )}

          <div className="absolute left-3 top-3 flex items-center gap-2">
            <PromoBadge kind={kind} text={badgeText} />
            {ended && (
              <span className="rounded-full bg-danger px-3 py-1 text-xs font-semibold text-white">
                Завершена
              </span>
            )}
          </div>
        </PromoImageArea>

        <div className="space-y-3 p-4">
          <h3 className="line-clamp-2 text-lg font-semibold leading-snug text-foreground">
            {promotion.title}
          </h3>

          <p className="line-clamp-2 text-sm text-foreground-muted">
            {stripDescriptionHtml(promotion.description) || 'Ограниченное предложение'}
          </p>

          <div className={cn('flex items-center gap-2 text-sm', ended ? 'text-danger' : 'text-foreground-muted')}>
            <Clock className="h-4 w-4 shrink-0" />
            <span>{ended ? 'Акция завершена' : `До конца: ${timeLeft}`}</span>
          </div>

          <div className="flex items-center gap-2 text-sm text-foreground-muted">
            <Users className="h-4 w-4 shrink-0" />
            <span>Уже {participants.toLocaleString('ru-RU')} человек</span>
          </div>

          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
            <Button asChild disabled={ended} className="w-full sm:w-auto">
              <Link href={toUtmCatalogHref(promotion)}>Забрать выгоду</Link>
            </Button>
            <div className="flex gap-2">
              <ShareButton promotion={promotion} />
              <CopyLinkButton />
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function Filters({ value, onChange }: { value: PromoKind; onChange: (v: PromoKind) => void }) {
  const chips: { id: PromoKind; label: string }[] = [
    { id: 'all', label: 'Все акции' },
    { id: 'discount', label: 'Скидка %' },
    { id: 'installment', label: 'Рассрочка 0%' },
    { id: 'gift', label: 'Подарок' },
    { id: 'product_of_day', label: 'Товар дня' },
  ];

  return (
    <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 py-2">
      {chips.map(c => {
        const active = c.id === value;
        return (
          <button
            key={c.id}
            type="button"
            onClick={() => onChange(c.id)}
            className={cn(
              'shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition-colors',
              active
                ? 'border-brand bg-brand text-white'
                : 'border-border bg-white text-foreground hover:bg-zinc-50'
            )}
          >
            {c.label}
          </button>
        );
      })}
    </div>
  );
}

function PromoHero({ onScrollToList }: { onScrollToList: () => void }) {
  return (
    <section className="relative overflow-hidden bg-background px-2 py-10 sm:px-4 sm:py-14 lg:px-6">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <Card className="relative overflow-hidden rounded-[32px] border border-border bg-white p-6 sm:p-10">
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.08]"
            aria-hidden
            style={{
              backgroundImage:
                'radial-gradient(circle at 10% 10%, rgba(34,197,94,0.35), transparent 40%), radial-gradient(circle at 80% 30%, rgba(59,130,246,0.25), transparent 45%), radial-gradient(circle at 40% 80%, rgba(245,158,11,0.25), transparent 45%)',
            }}
          />
          <div
            className="pointer-events-none absolute -right-10 -top-10 select-none text-[180px] font-semibold leading-none tracking-tight text-zinc-900/[0.04] sm:text-[220px]"
            aria-hidden
          >
            % :)
          </div>
          <div className="relative max-w-3xl">
            <h1 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
              Экономить — это умно. А у нас ещё и выгодно.
            </h1>
            <p className="mt-3 text-base text-foreground-muted sm:text-lg">
              Скидки, рассрочка 0%, подарки. Выбирай и забирай.
            </p>
            <div className="mt-6">
              <Button type="button" className="w-full sm:w-auto" onClick={onScrollToList}>
                Все акции
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

function ProductOfDayBlock({ promotion }: { promotion: Promotion }) {
  const timeLeft = usePromotionCountdown(promotion.end_date);
  return (
    <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Товар дня</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Суперпредложение — успей забрать.
            </p>
          </div>
        </div>

        <Card className="overflow-hidden p-0">
          <div className="grid gap-0 lg:grid-cols-[1.05fr_0.95fr]">
            <PromoImageArea>
              {promotion.image ? (
                <Image
                  src={getMediaUrl(promotion.image)}
                  alt=""
                  width={900}
                  height={700}
                  className="max-h-full max-w-full object-contain object-center"
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
              ) : (
                <div className="flex h-full items-center justify-center text-foreground-subtle">
                  Товар дня
                </div>
              )}
            </PromoImageArea>
            <div className="space-y-4 p-6 sm:p-8">
              <PromoBadge kind="product_of_day" text="Товар дня" />
              <h3 className="text-2xl font-semibold tracking-tight text-foreground">
                {promotion.title}
              </h3>
              <div className="text-sm text-foreground-muted">
                {stripDescriptionHtml(promotion.description) || 'Ограниченное предложение'}
              </div>
              <div className="rounded-2xl border border-border bg-white px-4 py-3">
                <div className="text-sm font-medium text-foreground-muted">До конца дня</div>
                <div className="mt-1 text-xl font-semibold text-foreground tabular-nums sm:text-2xl">
                  {timeLeft === 'Завершена' ? 'Завершена' : timeLeft}
                </div>
              </div>
              <Button asChild className="w-full">
                <Link href={toUtmCatalogHref(promotion)}>Купить со скидкой</Link>
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

function endOfTodayISO(): string {
  const d = new Date();
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

function productImageSlides(product: Product): { id: string; src: string; alt: string }[] {
  const imgs = [...(product.images ?? [])].sort((a, b) => {
    if (a.is_main && !b.is_main) return -1;
    if (!a.is_main && b.is_main) return 1;
    return (a.sort_order ?? 0) - (b.sort_order ?? 0);
  });
  return imgs
    .filter(img => img.image)
    .map(img => ({
      id: img.id,
      src: getMediaUrl(img.image)!,
      alt: product.title,
    }));
}

function ProductOfDayImageGallery({
  product,
  className,
  sizes,
}: {
  product: Product;
  className?: string;
  sizes: string;
}) {
  const slides = useMemo(() => productImageSlides(product), [product]);
  if (slides.length === 0) return null;

  const inner = (
    <div className={cn('relative aspect-square w-full', className)}>
      {slides.length > 1 ? (
        <Swiper
          modules={[Navigation]}
          navigation
          loop={slides.length > 2}
          slidesPerView={1}
          className="h-full w-full [&_.swiper-button-next]:right-2 [&_.swiper-button-prev]:left-2 [&_.swiper-button-next]:text-brand [&_.swiper-button-prev]:text-brand"
        >
          {slides.map((slide, i) => (
            <SwiperSlide key={`${slide.id}-${i}`}>
              <div className="relative aspect-square w-full">
                <Image
                  src={slide.src}
                  alt={slide.alt}
                  fill
                  sizes={sizes}
                  className="object-contain"
                  priority={i === 0}
                />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      ) : (
        <Image
          src={slides[0]!.src}
          alt={slides[0]!.alt}
          fill
          sizes={sizes}
          className="object-contain"
          priority
        />
      )}
    </div>
  );

  return inner;
}

function ProductOfDayProductBlock({ product }: { product: Product }) {
  const timeLeft = usePromotionCountdown(endOfTodayISO());
  const hasImages = (product.images ?? []).some(img => img.image);
  const old = product.old_price ? Number(product.old_price) : null;
  const cur = product.price ? Number(product.price) : null;
  const discount =
    product.discount_percent != null
      ? Math.round(Number(product.discount_percent))
      : old && cur && old > cur
        ? Math.round(((old - cur) / old) * 100)
        : null;

  return (
    <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Товар дня</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Суперпредложение — успей забрать.
            </p>
          </div>
        </div>

        <Card className="overflow-hidden p-0">
          <div className="flex flex-col lg:grid lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
            {hasImages ? (
              <div className="order-1 bg-white p-4 lg:hidden">
                <ProductOfDayImageGallery
                  product={product}
                  className="mx-auto w-full max-w-md"
                  sizes="100vw"
                />
              </div>
            ) : null}

            <div className="order-2 p-6 sm:p-8 lg:order-1">
              <PromoBadge kind="product_of_day" text="Товар дня" />
              <h3 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">
                {product.title}
              </h3>

              <div className="mt-3 flex flex-wrap items-end gap-3">
                <div className="text-3xl font-semibold leading-none text-foreground">
                  {cur != null && Number.isFinite(cur) ? Math.round(cur).toLocaleString('ru-RU') : '—'}{' '}
                  {CURRENCY_SYMBOL}
                </div>
                {old != null && cur != null && old > cur && (
                  <div className="pb-0.5 text-base font-medium text-foreground-muted line-through">
                    {Math.round(old).toLocaleString('ru-RU')} {CURRENCY_SYMBOL}
                  </div>
                )}
                {discount != null && discount > 0 && (
                  <span className="rounded-full bg-zinc-900 px-3 py-1 text-xs font-semibold text-white">
                    −{discount}%
                  </span>
                )}
              </div>

              <div className="mt-4 rounded-2xl border border-border bg-white px-4 py-3">
                <div className="text-sm font-medium text-foreground-muted">До конца дня</div>
                <div className="mt-1 text-xl font-semibold text-foreground tabular-nums sm:text-2xl">
                  {timeLeft === 'Завершена' ? 'Завершена' : timeLeft}
                </div>
              </div>

              <Button asChild className="mt-5 w-full">
                <Link
                  href={`/products/${product.slug}?utm_source=promotions&utm_medium=product_of_day&utm_campaign=${product.id}`}
                >
                  Купить со скидкой
                </Link>
              </Button>
            </div>

            {hasImages ? (
              <div className="order-3 hidden items-center justify-center bg-white p-6 lg:flex lg:order-2">
                <ProductOfDayImageGallery
                  product={product}
                  className="max-w-[280px] xl:max-w-[340px]"
                  sizes="(max-width: 1280px) 340px, 340px"
                />
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </section>
  );
}


function Faq() {
  const items = [
    {
      q: 'Можно ли совмещать скидку и рассрочку?',
      a: 'Зависит от условий конкретной акции и банка-партнёра. Обычно выбирается один тип выгоды.',
    },
    {
      q: 'Распространяется ли акция на товары с витрины?',
      a: 'Если товар участвует в акции и отмечен как активный — да. Уточняйте в карточке акции.',
    },
    {
      q: 'Как получить подарок?',
      a: 'Добавьте товар-участник в корзину и выполните условие акции. Подарок будет отображён при оформлении.',
    },
    {
      q: 'Что происходит после окончания акции?',
      a: 'Акция помечается как завершённая или скрывается. Мы стараемся держать список актуальным.',
    },
  ] as const;

  const [open, setOpen] = useState<number | null>(0);
  return (
    <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">FAQ по акциям</h2>
          <p className="mt-2 text-base text-foreground-muted sm:text-lg">Коротко и по делу.</p>
        </div>

        <div className="grid gap-3">
          {items.map((it, idx) => {
            const isOpen = open === idx;
            return (
              <Card key={it.q} className="overflow-hidden p-0">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                  onClick={() => setOpen(v => (v === idx ? null : idx))}
                >
                  <span className="text-sm font-semibold text-foreground sm:text-base">{it.q}</span>
                  <span className={cn('text-sm text-foreground-muted transition-transform', isOpen && 'rotate-180')}>
                    ↓
                  </span>
                </button>
                {isOpen && (
                  <div className="border-t border-border px-5 py-4 text-sm text-foreground-muted">
                    {it.a}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}

export default function PromotionsPage() {
  const listRef = useRef<HTMLDivElement>(null);
  const productOfDayRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState<PromoKind>('all');
  const [visibleCount, setVisibleCount] = useState(12);
  const didInitRef = useRef(false);
  const didScrollTopRef = useRef(false);

  const { data: promotions = [], isLoading, isError } = useQuery({
    queryKey: ['promotions', 'public'],
    queryFn: () => getPromotions({}),
  });

  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['products', 'promotions', { page_size: 48, ordering: 'rating_desc' }],
    queryFn: () => getProducts({ page_size: 48, ordering: 'rating_desc', page: 1 }),
    staleTime: 60 * 1000,
  });

  const products: Product[] = productsData?.results ?? [];
  const discountedProducts = useMemo(() => {
    return products.filter(p => {
      const old = p.old_price ? Number(p.old_price) : null;
      const cur = p.price ? Number(p.price) : null;
      const byOldPrice = old != null && cur != null && Number.isFinite(old) && Number.isFinite(cur) && old > cur;
      const byPercent = p.discount_percent != null && Number(p.discount_percent) > 0;
      return byOldPrice || byPercent;
    });
  }, [products]);

  const enriched = useMemo(() => {
    return promotions.map(p => ({ p, kind: guessKind(p) }));
  }, [promotions]);

  const filtered = useMemo(() => {
    if (filter === 'all') return enriched;
    return enriched.filter(x => x.kind === filter);
  }, [enriched, filter]);

  const productOfDay = useMemo(() => {
    const found = enriched.find(x => x.kind === 'product_of_day')?.p;
    if (found) return found;
    // fallback: самая “сильная” скидка по проценту
    const byPercent = enriched
      .filter(x => x.p.discount_type === 'percent')
      .sort((a, b) => Number(b.p.discount_value) - Number(a.p.discount_value));
    return byPercent[0]?.p ?? null;
  }, [enriched]);

  const productOfDayProduct = useMemo(() => {
    if (discountedProducts.length > 0) return discountedProducts[0];
    return products[0] ?? null;
  }, [discountedProducts, products]);

  const onScrollToList = () => {
    listRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useLayoutEffect(() => {
    // В AppShell используется анимация переходов (AnimatePresence),
    // и браузер/Next могут восстановить scroll. Жёстко фиксируем старт сверху.
    if (didScrollTopRef.current) return;
    didScrollTopRef.current = true;
    window.scrollTo(0, 0);
    requestAnimationFrame(() => {
      window.scrollTo(0, 0);
      requestAnimationFrame(() => window.scrollTo(0, 0));
    });
  }, []);

  useEffect(() => {
    if (!didInitRef.current) {
      didInitRef.current = true;
      return;
    }
    // UX: при смене чипса показываем контент сразу
    if (filter === 'product_of_day') {
      productOfDayRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    onScrollToList();
  }, [filter]);

  return (
    <>
      <PromoHero onScrollToList={onScrollToList} />

      <section className="bg-background px-2 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <Filters
            value={filter}
            onChange={v => {
              setFilter(v);
              setVisibleCount(12);
            }}
          />
        </div>
      </section>

      <div ref={productOfDayRef}>
        {productOfDay && <ProductOfDayBlock promotion={productOfDay} />}
        {!productOfDay && productOfDayProduct && <ProductOfDayProductBlock product={productOfDayProduct} />}
      </div>

      <section ref={listRef} className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
              {filter === 'discount'
                ? 'Скидки'
                : filter === 'installment'
                  ? 'Рассрочка 0%'
                  : filter === 'gift'
                    ? 'Подарки'
                    : filter === 'product_of_day'
                      ? 'Товар дня'
                      : 'Все акции'}
            </h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Выбирай тип выгоды и забирай.
            </p>
          </div>

          {filter === 'product_of_day' ? (
            <Card className="p-6 text-center text-foreground-muted">
              Товар дня показан выше.
            </Card>
          ) : filter === 'installment' ? (
            <div className="-mx-2 overflow-hidden sm:-mx-4 lg:-mx-6">
              <InstallmentZeroSection />
            </div>
          ) : filter === 'discount' ? (
            <>
              {productsLoading ? (
                <div className="flex min-h-[40vh] items-center justify-center">
                  <Loading />
                </div>
              ) : discountedProducts.length === 0 ? (
                <Card className="p-6 text-center text-foreground-muted">
                  Сейчас нет товаров со скидкой.
                </Card>
              ) : (
                <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 sm:gap-6 lg:grid-cols-3 lg:gap-7">
                  {discountedProducts.slice(0, visibleCount).map((p, idx) => (
                    <ProductCard
                      key={p.id}
                      product={p}
                      priority={idx === 0}
                      enableTilt
                      className="h-full"
                    />
                  ))}
                </div>
              )}

              {discountedProducts.length > visibleCount && (
                <div className="mt-6 flex justify-center">
                  <Button type="button" variant="secondary" onClick={() => setVisibleCount(v => v + 12)}>
                    Показать ещё
                  </Button>
                </div>
              )}
            </>
          ) : (
            <>
              {isLoading ? (
                <div className="flex min-h-[40vh] items-center justify-center">
                  <Loading />
                </div>
              ) : isError ? (
                <Card className="p-6 text-center text-danger">
                  Не удалось загрузить акции. Попробуйте позже.
                </Card>
              ) : filtered.length === 0 ? (
                <Card className="p-6 text-center text-foreground-muted">
                  Сейчас нет активных акций по выбранному фильтру.
                </Card>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {filtered.slice(0, visibleCount).map(({ p }) => (
                      <PromoCard key={p.id} promotion={p} />
                    ))}
                  </div>

                  {filtered.length > visibleCount && (
                    <div className="mt-6 flex justify-center">
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => setVisibleCount(v => v + 12)}
                      >
                        Показать ещё
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </section>

      <SubscribeDealsSection />
      <Faq />
    </>
  );
}
