'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { Award, ExternalLink, MapPin, Star, Wrench, Zap } from 'lucide-react';
import type { Manager, ManagerStore } from '@/lib/api/services/stores.service';
import { getManagers, getStores } from '@/lib/api/services/stores.service';
import { staffProfilePath } from '@/lib/staff-path';
import {
  fixManagerDisplayName,
  getManagerPhotoUrl,
  registerManagerStaticPhotos,
  type ManagerManifestPhotos,
} from '@/lib/staff/manager-photo';
import { getMediaUrl } from '@/lib/image-url';
import { getOrders, getRatingsSummary } from '@/lib/api/services/orders.service';
import { useAuth } from '@/lib/hooks/useAuth';
import type { Order } from '@/types/api';
import type { Store } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FilterSelect } from '@/components/ui/FilterSelect';
import { MOBILE_SECTION_BLEED_CLASS } from '@/lib/theme/spacing';
import { Loading } from '@/components/ui/Loading';
import { cn } from '@/lib/theme/utils';
import { formatRuDateLong } from '@/lib/format-date';
import { getPageGallery } from '@/lib/api/services/pageGallery.service';
import { PageHeroGallery } from '@/components/content/PageHeroGallery';

const StoresMap = dynamic(
  () => import('@/components/features/stores/StoresMap').then(m => ({ default: m.StoresMap })),
  {
    ssr: false,
    loading: () => <div className="h-72 w-full animate-pulse rounded-3xl bg-zinc-100" />,
  }
);

const WHATSAPP_NUMBER = '79184157788';
const WHATSAPP_LINK = `https://wa.me/${WHATSAPP_NUMBER}`;

function StarRating({ value, max = 5 }: { value: number; max?: number }) {
  const v = Math.min(max, Math.max(0, value));
  const full = Math.floor(v);
  const hasHalf = v - full >= 0.5;
  return (
    <div className="flex items-center gap-0.5" aria-label={`Оценка: ${value} из ${max}`}>
      {Array.from({ length: max }, (_, i) => {
        const filled = i < full;
        const half = i === full && hasHalf;
        return (
          <Star
            key={i}
            className={cn(
              'h-5 w-5',
              filled || half
                ? 'fill-amber-400 text-amber-400'
                : 'fill-zinc-200 text-zinc-200 dark:fill-zinc-600 dark:text-zinc-600'
            )}
            style={half ? { clipPath: 'inset(0 50% 0 0)' } : undefined}
            aria-hidden
          />
        );
      })}
    </div>
  );
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  const a = parts[0]?.[0] ?? '';
  const b = parts[1]?.[0] ?? '';
  return (a + b).toUpperCase();
}

function formatCountRu(n: number, one: string, few: string, many: string) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function buildDistribution(ratings: number[]) {
  const buckets = [0, 0, 0, 0, 0]; // 1..5
  ratings.forEach(r => {
    const v = Math.min(5, Math.max(1, Math.round(r)));
    buckets[v - 1] += 1;
  });
  const total = buckets.reduce((a, b) => a + b, 0);
  const perc = buckets.map(v => (total ? Math.round((v / total) * 100) : 0));
  return { buckets, perc, total };
}

function useAutoScrollRail(ref: React.RefObject<HTMLDivElement | null>, enabled: boolean, ms: number) {
  useEffect(() => {
    if (!enabled) return;
    const el = ref.current;
    if (!el) return;
    const t = window.setInterval(() => {
      const max = el.scrollWidth - el.clientWidth;
      if (max <= 0) return;
      const next = Math.min(max, el.scrollLeft + el.clientWidth);
      el.scrollTo({ left: next >= max ? 0 : next, behavior: 'smooth' });
    }, ms);
    return () => window.clearInterval(t);
  }, [enabled, ms, ref]);
}

function ordersEligibleForStore(orders: Order[], storeId: string) {
  return orders.filter(o => o.store === storeId && o.status !== 'cancelled');
}

function ManagerCard({
  manager,
  orders,
  isAuthenticated,
  ordersLoading,
}: {
  manager: Manager;
  orders: Order[];
  isAuthenticated: boolean;
  ordersLoading: boolean;
}) {
  const displayName = fixManagerDisplayName(manager);
  const photoUrl = getManagerPhotoUrl(manager);
  const avg = Number(manager.average_rating ?? 0);
  const count = Number(manager.ratings_count ?? 0);
  const isExpert = avg >= 4.9 && count >= 50;
  const storeId = manager.store?.id ?? '';
  const fromStore = useMemo(
    () => (storeId ? ordersEligibleForStore(orders, storeId) : []),
    [orders, storeId]
  );
  const canRate = fromStore.some(o => !o.has_rating);
  const orderForRate = fromStore.find(o => !o.has_rating);
  const reviewHref =
    canRate && orderForRate
      ? `/order-rate?order_id=${encodeURIComponent(orderForRate.id)}&manager_id=${encodeURIComponent(manager.id)}`
      : null;

  let reviewTitle: string | undefined;
  if (!isAuthenticated) {
    reviewTitle =
      'Войдите в аккаунт, с которого оформляли заказ в этом магазине — тогда сможете оставить отзыв.';
  } else if (!ordersLoading && fromStore.length === 0) {
    reviewTitle = 'Оставить отзыв можно после заказа в этом магазине.';
  } else if (!ordersLoading && fromStore.length > 0 && !canRate) {
    reviewTitle = 'Заказы в этом магазине уже оценены.';
  }

  return (
    <Card className="relative overflow-hidden rounded-3xl border border-border bg-white p-5 transition-transform duration-200 hover:scale-[1.02]">
      {isExpert && (
        <div className="absolute right-4 top-4 inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
          <Award className="h-4 w-4" />
          Эксперт года
        </div>
      )}

      <div className="flex items-start gap-4">
        <div className="relative h-[72px] w-[72px] shrink-0 overflow-hidden rounded-full bg-[radial-gradient(circle_at_30%_20%,rgba(34,197,94,0.35),transparent_55%),linear-gradient(180deg,#ffffff,#f6fff8)] ring-1 ring-black/5">
          {photoUrl ? (
            <Image
              src={photoUrl.startsWith('/') ? photoUrl : getMediaUrl(photoUrl)}
              alt={displayName}
              fill
              className="object-cover"
              sizes="72px"
              unoptimized={photoUrl.startsWith('/')}
            />
          ) : (
            <span className="flex size-full items-center justify-center text-lg font-bold text-foreground">
              {initials(displayName)}
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          {manager.slug ? (
            <Link
              href={staffProfilePath(manager.slug)}
              className="truncate text-base font-semibold text-foreground hover:text-info hover:underline"
            >
              {displayName}
            </Link>
          ) : (
            <p className="truncate text-base font-semibold text-foreground">{displayName}</p>
          )}
          <p className="mt-0.5 text-sm text-foreground-muted">
            {manager.job_title?.trim() || 'Ведущий консультант'}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <StarRating value={avg} />
            <span className="font-semibold text-foreground">{avg.toFixed(1)}</span>
            <span className="text-foreground-muted">
              ({count} {formatCountRu(count, 'отзыв', 'отзыва', 'отзывов')})
            </span>
          </div>
          <p className="mt-2 flex items-center gap-2 text-sm text-foreground-muted">
            <MapPin className="h-4 w-4 shrink-0" />
            <span className="truncate">
              {manager.store?.name}
              {manager.store?.city ? `, ${manager.store.city}` : ''}
            </span>
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2">
        {manager.slug ? (
          <Button asChild variant="outline" className="w-full">
            <Link href={staffProfilePath(manager.slug)}>Профиль консультанта</Link>
          </Button>
        ) : null}
        {reviewHref ? (
          <Button asChild className="w-full">
            <Link href={reviewHref}>
              <Star className="mr-2 h-4 w-4" />
              Оставить отзыв
            </Link>
          </Button>
        ) : (
          <Button
            type="button"
            className="w-full"
            disabled={ordersLoading || !isAuthenticated || fromStore.length === 0 || !canRate}
            title={reviewTitle}
          >
            <Star className="mr-2 h-4 w-4" />
            {ordersLoading && isAuthenticated ? 'Проверка заказов…' : 'Оставить отзыв'}
          </Button>
        )}
        {!isAuthenticated && (
          <Button asChild variant="outline" size="sm" className="w-full">
            <Link href={`/login?next=${encodeURIComponent('/about')}`}>Войти в аккаунт</Link>
          </Button>
        )}
      </div>
    </Card>
  );
}

function ReviewCard({
  rating,
  comment,
  createdAt,
  managerName,
}: {
  rating: number;
  comment: string | null;
  createdAt: string;
  managerName?: string | null;
}) {
  return (
    <Card className="w-[320px] shrink-0 snap-start rounded-3xl border border-border bg-white p-5 sm:w-[360px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-foreground">
            {managerName ? `${managerName}` : 'Покупатель'}
            <span className="ml-2 text-xs font-medium text-foreground-muted">Владикавказ</span>
          </p>
          <div className="mt-2 flex items-center gap-2">
            <StarRating value={rating} />
            <span className="text-sm font-semibold text-foreground">{rating.toFixed(1)}</span>
          </div>
        </div>
        <span className="rounded-full bg-zinc-900 px-3 py-1 text-[11px] font-semibold text-white">
          Покупка подтверждена
        </span>
      </div>
      <p className="mt-4 line-clamp-3 text-sm text-foreground-muted">
        {comment?.trim() || 'Спасибо! Всё понравилось — быстро и удобно.'}
      </p>
      <p className="mt-4 text-xs text-foreground-muted">
        {formatRuDateLong(createdAt)}
      </p>
    </Card>
  );
}

export function AboutContent() {
  useEffect(() => {
    fetch('/menegers/manifest.json')
      .then(r => r.json())
      .then((d: { managers?: Record<string, ManagerManifestPhotos> }) => {
        if (d.managers) registerManagerStaticPhotos(d.managers);
      })
      .catch(() => {});
  }, []);

  const { isAuthenticated } = useAuth();
  const { data: ordersData, isLoading: ordersLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getOrders(),
    enabled: isAuthenticated,
  });
  const orders = ordersData?.results ?? [];

  const { data: managers = [], isLoading: managersLoading } = useQuery({
    queryKey: ['managers'],
    queryFn: getManagers,
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['ratings-summary'],
    queryFn: getRatingsSummary,
  });

  const { data: storesData } = useQuery({
    queryKey: ['stores', 'about', 'active'],
    queryFn: () => getStores({ is_active: true }),
    staleTime: 60 * 1000,
  });

  const { data: aboutHeroGallery = [] } = useQuery({
    queryKey: ['page-gallery', 'about_hero'],
    queryFn: () => getPageGallery('about_hero'),
    staleTime: 5 * 60 * 1000,
  });

  const stores: Store[] = storesData?.results ?? [];

  const railManagersRef = useRef<HTMLDivElement | null>(null);
  const railReviewsRef = useRef<HTMLDivElement | null>(null);

  const [filterCity, setFilterCity] = useState<string>('all');
  const [filterStoreId, setFilterStoreId] = useState<string>('all');

  useAutoScrollRail(railReviewsRef, true, 5000);

  const managerCities = useMemo(() => {
    const set = new Set(managers.map(m => m.store.city).filter(Boolean));
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'ru'));
  }, [managers]);

  const storesForFilter = useMemo(() => {
    const map = new Map<string, ManagerStore>();
    for (const m of managers) {
      if (filterCity !== 'all' && m.store.city !== filterCity) continue;
      map.set(m.store.id, m.store);
    }
    return Array.from(map.values()).sort(
      (a, b) => a.city.localeCompare(b.city, 'ru') || a.name.localeCompare(b.name, 'ru')
    );
  }, [managers, filterCity]);

  const filteredManagers = useMemo(
    () =>
      managers.filter(m => {
        if (filterCity !== 'all' && m.store.city !== filterCity) return false;
        if (filterStoreId !== 'all' && m.store.id !== filterStoreId) return false;
        return true;
      }),
    [managers, filterCity, filterStoreId]
  );

  useEffect(() => {
    if (filterStoreId === 'all') return;
    if (!storesForFilter.some(s => s.id === filterStoreId)) {
      setFilterStoreId('all');
    }
  }, [filterCity, storesForFilter, filterStoreId]);

  const avg = summary?.average ?? 0;
  const count = summary?.count ?? 0;
  const recent = summary?.recent ?? [];
  const dist = useMemo(() => buildDistribution(recent.map(r => r.rating)), [recent]);

  return (
    <div className="bg-background">
      {/* HERO */}
      <section className="bg-background px-4 py-10 sm:px-4 sm:py-14 lg:px-6">
        <div className="mx-auto w-full max-w-7xl sm:px-6 lg:px-8">
          <Card className="relative overflow-hidden rounded-[32px] border border-border bg-white p-4 sm:p-10">
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.10]"
              aria-hidden
              style={{
                backgroundImage:
                  'radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.35), transparent 45%), radial-gradient(circle at 70% 30%, rgba(59, 130, 246, 0.22), transparent 45%), radial-gradient(circle at 40% 90%, rgba(245, 158, 11, 0.18), transparent 50%)',
              }}
            />
            <div className="relative grid gap-8 max-md:flex max-md:flex-col lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-brand">О компании Ringoo</p>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                  Ringoo — техника, которой доверяют
                </h1>
                <p className="mt-3 text-base text-foreground-muted sm:text-lg">
                  Крупнейшая сеть магазинов электроники в Северной Осетии. Работаем с 2015 года.
                </p>

                <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">10 000+</p>
                    <p className="text-sm text-foreground-muted">довольных клиентов</p>
                  </div>
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">5</p>
                    <p className="text-sm text-foreground-muted">магазинов во Владикавказе и республике</p>
                  </div>
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">2 года</p>
                    <p className="text-sm text-foreground-muted">гарантии на технику</p>
                  </div>
                </div>

                <div className="mt-7 flex flex-col gap-2 sm:flex-row">
                  <Button asChild className="w-full sm:w-auto">
                    <Link href="/stores">
                      Посмотреть магазины <ExternalLink className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>

              <div
                className={cn(
                  'max-md:order-last max-md:col-span-full',
                  MOBILE_SECTION_BLEED_CLASS,
                  'md:mx-0 md:w-full'
                )}
              >
                <div className="relative overflow-hidden max-md:rounded-none md:rounded-3xl md:border md:border-border md:bg-[radial-gradient(circle_at_20%_20%,rgba(34,197,94,0.22),transparent_55%),linear-gradient(180deg,#ffffff,#f6fff8)] md:p-6 lg:p-10">
                  <div className="max-md:px-4 md:px-0">
                    <p className="text-sm font-semibold text-foreground">Команда Ringoo</p>
                    <p className="mt-2 text-sm text-foreground-muted">
                      Консультации в магазине и онлайн — быстро, честно и без лишних обещаний.
                    </p>
                  </div>
                  <div className="mt-4 md:mt-6">
                    <PageHeroGallery images={aboutHeroGallery} fullBleed />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* МИССИЯ И ЦЕННОСТИ */}
      <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Наша миссия и ценности</h2>
            <p className="mt-2 max-w-3xl text-base text-foreground-muted sm:text-lg">
              Мы делаем современную технику доступной и понятной. Без скрытых комиссий, без долгой доставки,
              без равнодушия. Потому что верим: хороший сервис начинается с человеческого отношения.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="rounded-3xl border border-border bg-white p-6">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700">
                <Award className="h-5 w-5" />
              </div>
              <p className="text-base font-semibold text-foreground">Честность</p>
              <p className="mt-1 text-sm text-foreground-muted">Цена как на витрине.</p>
            </Card>
            <Card className="rounded-3xl border border-border bg-white p-6">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-50 text-sky-700">
                <Zap className="h-5 w-5" />
              </div>
              <p className="text-base font-semibold text-foreground">Скорость</p>
              <p className="mt-1 text-sm text-foreground-muted">Доставка за 2 часа.</p>
            </Card>
            <Card className="rounded-3xl border border-border bg-white p-6">
              <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                <Wrench className="h-5 w-5" />
              </div>
              <p className="text-base font-semibold text-foreground">Поддержка</p>
              <p className="mt-1 text-sm text-foreground-muted">Сервисный центр и гарантия.</p>
            </Card>
          </div>
        </div>
      </section>

      {/* КОМАНДА */}
      <section id="managers" className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Вас консультируют лучшие</h2>
              <p className="mt-2 text-base text-foreground-muted sm:text-lg">
                Наши менеджеры — эксперты, которые помогут выбрать и не дадут ошибиться.
              </p>
            </div>
          </div>

          {managersLoading ? (
            <div className="flex min-h-[160px] items-center justify-center">
              <Loading />
            </div>
          ) : managers.length === 0 ? (
            <Card className="p-6 text-center text-foreground-muted">Список менеджеров пока пуст.</Card>
          ) : (
            <>
              <Card className="mb-6 rounded-3xl border border-border bg-white p-4 sm:p-5">
                <p className="mb-3 text-sm font-semibold text-foreground">Фильтр по магазину</p>
                <div className="grid gap-4 sm:grid-cols-2 lg:max-w-3xl">
                  <FilterSelect
                    id="about-managers-city"
                    label="Город"
                    value={filterCity}
                    onChange={e => {
                      setFilterCity(e.target.value);
                      setFilterStoreId('all');
                    }}
                  >
                    <option value="all">Все города</option>
                    {managerCities.map(city => (
                      <option key={city} value={city}>
                        {city}
                      </option>
                    ))}
                  </FilterSelect>
                  <FilterSelect
                    id="about-managers-store"
                    label="Магазин"
                    value={filterStoreId}
                    onChange={e => setFilterStoreId(e.target.value)}
                  >
                    <option value="all">Все магазины{filterCity !== 'all' ? ` (${filterCity})` : ''}</option>
                    {storesForFilter.map(s => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {filterCity === 'all' && s.city ? ` — ${s.city}` : ''}
                      </option>
                    ))}
                  </FilterSelect>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-foreground-muted">
                  <span>
                    Показано:{' '}
                    <strong className="text-foreground">{filteredManagers.length}</strong> из {managers.length}
                  </span>
                  {(filterCity !== 'all' || filterStoreId !== 'all') && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setFilterCity('all');
                        setFilterStoreId('all');
                      }}
                    >
                      Сбросить фильтр
                    </Button>
                  )}
                </div>
              </Card>

              {filteredManagers.length === 0 ? (
                <Card className="p-6 text-center text-foreground-muted">
                  Нет менеджеров по выбранным условиям. Измените город или магазин.
                </Card>
              ) : (
                <>
                  {/* Desktop grid — все менеджеры по фильтру */}
                  <div className="hidden gap-5 lg:grid lg:grid-cols-3 xl:grid-cols-4">
                    {filteredManagers.map(m => (
                      <ManagerCard
                        key={m.id}
                        manager={m}
                        orders={orders}
                        isAuthenticated={isAuthenticated}
                        ordersLoading={ordersLoading}
                      />
                    ))}
                  </div>

                  {/* Mobile rail */}
                  <div
                    ref={railManagersRef}
                    className="no-scrollbar flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 lg:hidden"
                  >
                    {filteredManagers.map(m => (
                      <div key={m.id} className="w-[340px] shrink-0 snap-start">
                        <ManagerCard
                          manager={m}
                          orders={orders}
                          isAuthenticated={isAuthenticated}
                          ordersLoading={ordersLoading}
                        />
                      </div>
                    ))}
                  </div>
                  <p className="mt-6 text-center text-xs text-foreground-muted">
                    Размещение фотографий и ФИО сотрудников на сайте осуществляется с их согласия.{' '}
                    <Link href="/docs/privacy" className="underline hover:no-underline">
                      Политика конфиденциальности
                    </Link>
                    .
                  </p>
                </>
              )}
            </>
          )}
        </div>
      </section>

      {/* ОБЩАЯ ОЦЕНКА */}
      <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Что говорят о нас покупатели</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Рейтинг магазинов Ringoo на основе реальных отзывов
            </p>
          </div>

          <Card className="rounded-[32px] border border-border bg-white p-6 sm:p-10">
            {summaryLoading || !summary ? (
              <div className="flex min-h-[180px] items-center justify-center">
                <Loading />
              </div>
            ) : (
              <div className="grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
                <div className="text-center lg:text-left">
                  <div className="text-[64px] font-semibold leading-none tracking-tight text-foreground sm:text-[84px]">
                    {avg.toFixed(1)}
                  </div>
                  <div className="mt-3 flex justify-center lg:justify-start">
                    <StarRating value={avg} />
                  </div>
                  <p className="mt-3 text-sm text-foreground-muted">
                    {count.toLocaleString('ru-RU')} {formatCountRu(count, 'отзыв', 'отзыва', 'отзывов')}
                  </p>
                  <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center lg:justify-start">
                    <Button asChild variant="secondary">
                      <a href={WHATSAPP_LINK} target="_blank" rel="noopener noreferrer">
                        Оставить отзыв
                      </a>
                    </Button>
                    <Button asChild variant="secondary">
                      <Link href="/profile">Все отзывы</Link>
                    </Button>
                  </div>
                </div>

                <div className="space-y-3">
                  {[5, 4, 3, 2, 1].map(stars => {
                    const idx = stars - 1;
                    const pct = dist.perc[idx] ?? 0;
                    return (
                      <div key={stars} className="flex items-center gap-3">
                        <div className="w-16 text-sm font-medium text-foreground">
                          {stars} <span className="text-amber-500">★</span>
                        </div>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-zinc-100">
                          <div className="h-full rounded-full bg-zinc-900" style={{ width: `${pct}%` }} />
                        </div>
                        <div className="w-12 text-right text-sm text-foreground-muted">{pct}%</div>
                      </div>
                    );
                  })}
                  <p className="pt-2 text-xs text-foreground-muted">
                    Распределение рассчитано по последним отзывам.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </section>

      {/* ОТЗЫВЫ (карусель) */}
      <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
                Реальные отзывы из наших магазинов
              </h2>
              <p className="mt-2 text-base text-foreground-muted sm:text-lg">
                Автопрокрутка каждые 5 секунд + свайп.
              </p>
            </div>
          </div>

          <div
            ref={railReviewsRef}
            className="no-scrollbar flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2"
          >
            {(recent.length > 0 ? recent : [
              { rating: 5, comment: 'Быстро помогли выбрать, всё объяснили.', created_at: new Date().toISOString(), manager_name: 'Алан К.' },
              { rating: 4.8, comment: 'Отличный сервис, доставка в тот же день.', created_at: new Date().toISOString(), manager_name: 'Марина С.' },
              { rating: 4.9, comment: 'Понравилось отношение — без навязывания.', created_at: new Date().toISOString(), manager_name: 'Руслан М.' },
            ]).slice(0, 8).map((r, i) => (
              <ReviewCard
                key={`${r.created_at}-${i}`}
                rating={r.rating}
                comment={r.comment}
                createdAt={r.created_at}
                managerName={r.manager_name}
              />
            ))}
          </div>
        </div>
      </section>

      {/* МАГАЗИНЫ (карта + адреса) */}
      <section className="bg-background px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Приходите в гости</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Карта и адреса наших магазинов.
            </p>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr] lg:items-start">
            <StoresMap stores={stores} />

            <Card className="rounded-3xl border border-border bg-white p-5">
              <p className="text-sm font-semibold text-foreground">Адреса</p>
              <div className="mt-3 grid gap-3">
                {stores.slice(0, 5).map(s => (
                  <div key={s.id} className="rounded-2xl border border-border bg-white p-4">
                    <p className="text-sm font-semibold text-foreground">{s.city}</p>
                    <p className="mt-1 text-sm text-foreground-muted">{s.address}</p>
                    <div className="mt-3 flex gap-2">
                      <Button asChild size="sm" variant="secondary">
                        <a
                          href={`https://yandex.ru/maps/?text=${encodeURIComponent(`${s.city}, ${s.address}`)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Построить маршрут <ExternalLink className="ml-2 h-4 w-4" />
                        </a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              <Button asChild variant="secondary" className="mt-4 w-full">
                <Link href="/stores">Все магазины</Link>
              </Button>
            </Card>
          </div>
        </div>
      </section>

      {/* КАРЬЕРА (опционально) */}
      <section className="bg-background px-2 pb-12 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <Card className="rounded-[32px] border border-border bg-white p-6 sm:p-10">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-lg font-semibold text-foreground">Хотите работать в команде Ringoo?</p>
                <p className="mt-1 text-sm text-foreground-muted">
                  Отправьте резюме — мы свяжемся, если будет подходящая позиция.
                </p>
              </div>
              <Button asChild className="w-full sm:w-auto">
                <a href="mailto:hr@ringoo.ru?subject=Резюме%20в%20Ringoo">
                  Отправить резюме <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}

