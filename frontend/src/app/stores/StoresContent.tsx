'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Clock,
  Crosshair,
  ExternalLink,
  MapPin,
  Navigation,
  Search,
  ShoppingBag,
} from 'lucide-react';
import type { Store, Stock } from '@/types';
import { getStores, getProductStock } from '@/lib/api/services/stores.service';
import { getProductAutocomplete } from '@/lib/api/services/products.service';
import type { ProductAutocompleteItem } from '@/lib/api/services/products.service';
import { addToCart, getCart } from '@/lib/api/services/cart.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { FilterSelect } from '@/components/ui/FilterSelect';
import { MOBILE_SECTION_BLEED_CLASS } from '@/lib/theme/spacing';
import { Loading } from '@/components/ui/Loading';
import { cn } from '@/lib/theme/utils';
import { getPageGallery } from '@/lib/api/services/pageGallery.service';
import { PageHeroGallery } from '@/components/content/PageHeroGallery';
import {
  fetchMagazinGalleryUrls,
  magazinUrlsToGalleryImages,
} from '@/lib/stores/magazin-gallery';

const StoresMapDynamic = dynamic(
  () =>
    import('@/components/features/stores/StoresMap').then(m => ({
      default: m.StoresMap,
    })),
  {
    loading: () => <div className="h-80 w-full animate-pulse rounded-3xl bg-zinc-100" />,
    ssr: false,
  }
);

const DAY_KEY: Record<number, keyof NonNullable<Store['working_hours']>> = {
  0: 'sunday',
  1: 'monday',
  2: 'tuesday',
  3: 'wednesday',
  4: 'thursday',
  5: 'friday',
  6: 'saturday',
};

const DAY_LABELS: Record<string, string> = {
  monday: 'Пн',
  tuesday: 'Вт',
  wednesday: 'Ср',
  thursday: 'Чт',
  friday: 'Пт',
  saturday: 'Сб',
  sunday: 'Вс',
};

function formatWorkingHours(working_hours: Record<string, string> | null): string {
  if (!working_hours || Object.keys(working_hours).length === 0) return '—';
  const order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  return order
    .filter(key => working_hours[key])
    .map(key => `${DAY_LABELS[key] ?? key}: ${working_hours[key]}`)
    .join(', ');
}

function parseWorkingHoursRange(value: string): { startMin: number; endMin: number } | null {
  const v = value.trim().toLowerCase();
  if (!v || v.includes('выход') || v.includes('закрыт') || v === '—') return null;

  // Most common formats: "9-21", "09-21", "09:00-21:00", "9:00–21:00"
  const m = v.match(/(\d{1,2})(?::(\d{2}))?\s*[-–—]\s*(\d{1,2})(?::(\d{2}))?/);
  if (!m) return null;
  const sh = Number(m[1]);
  const sm = Number(m[2] ?? '0');
  const eh = Number(m[3]);
  const em = Number(m[4] ?? '0');
  if (!Number.isFinite(sh) || !Number.isFinite(sm) || !Number.isFinite(eh) || !Number.isFinite(em)) {
    return null;
  }
  const startMin = sh * 60 + sm;
  const endMin = eh * 60 + em;
  if (startMin < 0 || startMin >= 24 * 60) return null;
  if (endMin <= 0 || endMin > 24 * 60) return null;
  return { startMin, endMin };
}

function isOpenNow(store: Store, now = new Date()): boolean | null {
  const wh = store.working_hours;
  if (!wh) return null;
  const key = DAY_KEY[now.getDay()];
  if (!key) return null;
  const raw = wh[key];
  if (!raw) return null;
  const range = parseWorkingHoursRange(raw);
  if (!range) return false;
  const minutes = now.getHours() * 60 + now.getMinutes();
  // Support overnight "21-2" if ever used
  if (range.endMin < range.startMin) {
    return minutes >= range.startMin || minutes <= range.endMin;
  }
  return minutes >= range.startMin && minutes <= range.endMin;
}

function haversineKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const toRad = (x: number) => (x * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const s =
    Math.sin(dLat / 2) ** 2 + Math.sin(dLon / 2) ** 2 * Math.cos(lat1) * Math.cos(lat2);
  return 2 * R * Math.asin(Math.sqrt(s));
}

function buildYandexRouteUrl(store: Store, user?: { lat: number; lon: number }): string {
  const storeHasCoords = Boolean(store.coordinates);
  if (storeHasCoords && user) {
    const storeLon = store.coordinates!.longitude;
    const storeLat = store.coordinates!.latitude;
    return `https://yandex.ru/maps/?rtext=~${user.lat},${user.lon}&rtt=auto&ruri=ymapsbm1://geo?ll=${storeLon},${storeLat}`;
  }
  if (storeHasCoords) {
    const lon = store.coordinates!.longitude;
    const lat = store.coordinates!.latitude;
    return `https://yandex.ru/maps/?pt=${lon},${lat}&z=16`;
  }
  const query = encodeURIComponent([store.city, store.address].filter(Boolean).join(', '));
  return `https://yandex.ru/maps/?text=${query}`;
}

function quantityLabel(qty: number): string {
  if (qty <= 0) return 'Нет';
  if (qty >= 10) return 'Много';
  return `${qty} шт.`;
}

export function StoresContent() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const heroMapRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const storeItemRefs = useRef<Record<string, HTMLLIElement | null>>({});

  const [search, setSearch] = useState('');
  const [city, setCity] = useState<string>('all');
  const [onlyOpenNow, setOnlyOpenNow] = useState(false);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [geoError, setGeoError] = useState<string>('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['stores', 'list'],
    queryFn: () => getStores({ is_active: true }),
  });

  const { data: magazinStaticUrls = [] } = useQuery({
    queryKey: ['magazins', 'static-manifest'],
    queryFn: fetchMagazinGalleryUrls,
    staleTime: 24 * 60 * 60 * 1000,
  });

  const { data: storesHeroGalleryApi = [] } = useQuery({
    queryKey: ['page-gallery', 'stores_hero'],
    queryFn: () => getPageGallery('stores_hero'),
    staleTime: 5 * 60 * 1000,
  });

  const storesHeroGallery = useMemo(() => {
    if (magazinStaticUrls.length > 0) {
      return magazinUrlsToGalleryImages(magazinStaticUrls);
    }
    return storesHeroGalleryApi;
  }, [magazinStaticUrls, storesHeroGalleryApi]);

  const stores: Store[] = data?.results ?? [];

  const availableCities = useMemo(() => {
    const set = new Set(stores.map(s => s.city).filter(Boolean));
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'ru'));
  }, [stores]);

  const filteredStores = useMemo(() => {
    const q = search.trim().toLowerCase();
    return stores
      .filter(s => (city === 'all' ? true : s.city === city))
      .filter(s => {
        if (!q) return true;
        return (
          s.name.toLowerCase().includes(q) ||
          s.city.toLowerCase().includes(q) ||
          s.address.toLowerCase().includes(q)
        );
      })
      .filter(s => {
        if (!onlyOpenNow) return true;
        return isOpenNow(s) === true;
      });
  }, [stores, city, search, onlyOpenNow]);

  const storesWithDistance = useMemo(() => {
    if (!userLocation) return filteredStores.map(s => ({ store: s, distanceKm: null }));
    return filteredStores.map(s => {
      if (!s.coordinates) return { store: s, distanceKm: null };
      const lat = Number(s.coordinates.latitude);
      const lon = Number(s.coordinates.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return { store: s, distanceKm: null };
      return { store: s, distanceKm: haversineKm(userLocation, { lat, lon }) };
    });
  }, [filteredStores, userLocation]);

  const sortedStores = useMemo(() => {
    const list = [...storesWithDistance];
    list.sort((a, b) => {
      // selected store stays on top for better UX
      if (selectedStoreId) {
        const aSel = a.store.id === selectedStoreId;
        const bSel = b.store.id === selectedStoreId;
        if (aSel && !bSel) return -1;
        if (!aSel && bSel) return 1;
      }
      const ad = a.distanceKm;
      const bd = b.distanceKm;
      if (ad == null && bd == null) return a.store.name.localeCompare(b.store.name, 'ru');
      if (ad == null) return 1;
      if (bd == null) return -1;
      return ad - bd;
    });
    return list;
  }, [storesWithDistance, selectedStoreId]);

  useEffect(() => {
    if (!selectedStoreId) return;
    const el = storeItemRefs.current[selectedStoreId];
    if (el) {
      el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedStoreId]);

  const requestGeolocation = () => {
    setGeoError('');
    if (!('geolocation' in navigator)) {
      setGeoError('Геолокация недоступна в этом браузере.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      },
      err => {
        setGeoError(err.message || 'Не удалось получить геолокацию.');
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60_000 }
    );
  };

  // --- Stock block ---
  const [productQuery, setProductQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<ProductAutocompleteItem | null>(null);
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  const { data: autocomplete = [], isLoading: autocompleteLoading } = useQuery({
    queryKey: ['products', 'autocomplete', productQuery],
    queryFn: () => getProductAutocomplete(productQuery),
    enabled: productQuery.trim().length >= 2,
    staleTime: 60 * 1000,
  });

  const { data: stock = [], isLoading: stockLoading } = useQuery({
    queryKey: ['product-stock', selectedProduct?.id, city],
    queryFn: async () => {
      const all = await getProductStock(selectedProduct!.id);
      return all;
    },
    enabled: Boolean(selectedProduct?.id),
    staleTime: 5 * 60 * 1000,
  });

  const stockByStore = useMemo(() => {
    const map = new Map<string, Stock>();
    for (const s of stock) map.set(s.store, s);
    return map;
  }, [stock]);

  const storesForStock = useMemo(() => {
    const base = city === 'all' ? stores : stores.filter(s => s.city === city);
    return base
      .map(s => ({
        store: s,
        available: stockByStore.get(s.id)?.available_quantity ?? 0,
      }))
      .filter(x => selectedProduct ? true : false);
  }, [stores, city, stockByStore, selectedProduct]);

  const hasStockInFilteredStores = useMemo(
    () => (selectedProduct ? storesForStock.some(x => x.available > 0) : false),
    [selectedProduct, storesForStock]
  );

  const addToCartMutation = useMutation({
    mutationFn: async (vars: { productId: string; storeId: string }) => {
      const next = await addToCart(vars.productId, 1, vars.storeId);
      return next;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      // keep cart endpoint consistent with rest of app
      queryClient.invalidateQueries({ queryKey: ['cart', 'get'] });
      queryClient.invalidateQueries({ queryKey: ['cart', 'me'] });
    },
  });

  const goToCheckoutPickup = async () => {
    // Warm cart query if it exists in app (best effort)
    try {
      await queryClient.fetchQuery({ queryKey: ['cart'], queryFn: getCart });
    } catch {
      // ignore
    }
    router.push('/checkout?step=delivery');
  };

  if (isLoading) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <Loading />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <p className="text-sm text-red-600 dark:text-red-400">
          Не удалось загрузить список магазинов. Попробуйте позже.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-background">
      {/* Блок 1. HERO */}
      <section className="px-2 py-4 sm:px-4 sm:py-6 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <Card className="relative overflow-hidden rounded-[32px] border border-border bg-white p-4 sm:p-6">
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.10]"
              aria-hidden
              style={{
                backgroundImage:
                  'radial-gradient(circle at 12% 14%, rgba(46, 125, 50, 0.35), transparent 45%), radial-gradient(circle at 75% 35%, rgba(59, 130, 246, 0.18), transparent 45%), radial-gradient(circle at 40% 90%, rgba(245, 158, 11, 0.12), transparent 50%)',
              }}
            />

            <div className="relative grid grid-cols-1 gap-5 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
              <div>
                <p className="text-sm font-semibold text-brand">Локальное присутствие Ringoo</p>
                <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl lg:text-4xl">
                  Магазины Ringoo — рядом с домом и работой
                </h1>
                <p className="mt-3 max-w-2xl text-base text-foreground-muted sm:text-lg">
                  Самовывоз за 15 минут. Проверка техники до оплаты. Консультация эксперта.
                </p>

                <div className="mt-4 grid gap-2 sm:grid-cols-3 sm:gap-3">
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">{stores.length}</p>
                    <p className="text-sm text-foreground-muted">магазинов в РСО-Алания</p>
                  </div>
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">9–21</p>
                    <p className="text-sm text-foreground-muted">работаем ежедневно</p>
                  </div>
                  <div className="rounded-2xl border border-border bg-white/70 px-4 py-3 backdrop-blur">
                    <p className="text-2xl font-semibold text-foreground">Самовывоз</p>
                    <p className="text-sm text-foreground-muted">без ожидания доставки</p>
                  </div>
                </div>

                <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                  <Button
                    className="w-full sm:w-auto"
                    onClick={() => heroMapRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                  >
                    Найти ближайший магазин <MapPin className="ml-2 h-4 w-4" />
                  </Button>
                  <Button
                    variant="secondary"
                    className="w-full sm:w-auto"
                    onClick={requestGeolocation}
                    title="Покажем расстояние до магазинов, если разрешите геолокацию"
                  >
                    Геолокация <Crosshair className="ml-2 h-4 w-4" />
                  </Button>
                </div>
                {geoError && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{geoError}</p>}

                <div className="mt-4 md:hidden">
                  <p className="text-sm font-semibold text-foreground">Визит без сюрпризов</p>
                  <ul className="mt-3 space-y-2 text-sm text-foreground-muted">
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-600" />
                      Проверьте наличие товара до поездки
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-600" />
                      Постройте маршрут в 1 клик
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-600" />
                      Заберите покупку сегодня
                    </li>
                  </ul>
                </div>
              </div>

              <div
                className={cn(
                  'max-md:col-span-full',
                  MOBILE_SECTION_BLEED_CLASS,
                  'md:mx-0 md:w-full'
                )}
              >
                <div className="relative overflow-hidden max-md:rounded-none md:rounded-3xl md:border md:border-border md:bg-[radial-gradient(circle_at_20%_20%,rgba(46,125,50,0.18),transparent_55%),linear-gradient(180deg,#ffffff,#f7faf7)] md:p-4 lg:p-6">
                  <div className="hidden md:block">
                    <p className="text-sm font-semibold text-foreground">Визит без сюрпризов</p>
                    <ul className="mt-3 space-y-2 text-sm text-foreground-muted">
                      <li className="flex items-start gap-2">
                        <span className="mt-0.5 inline-block h-2 w-2 rounded-full bg-emerald-600" />
                        Проверьте наличие товара до поездки
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="mt-0.5 inline-block h-2 w-2 rounded-full bg-emerald-600" />
                        Постройте маршрут в 1 клик
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="mt-0.5 inline-block h-2 w-2 rounded-full bg-emerald-600" />
                        Заберите покупку сегодня
                      </li>
                    </ul>
                  </div>
                  <div className="mt-0 max-h-[min(50vh,360px)] md:mt-4 md:max-h-[min(42vh,320px)]">
                    <PageHeroGallery
                      images={storesHeroGallery}
                      fullBleed
                      className="h-full max-h-[min(50vh,360px)] md:max-h-[min(42vh,320px)]"
                    />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Блок 2. Поиск и фильтры */}
      <section className="px-2 pb-2 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <Card className="rounded-3xl border border-border bg-white p-4 sm:p-5">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
              <div className="grid gap-4 sm:grid-cols-2">
                <FilterSelect
                  id="stores-city"
                  label="Город / район"
                  value={city}
                  onChange={e => setCity(e.target.value)}
                >
                  <option value="all">Все города</option>
                  {availableCities.map(c => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </FilterSelect>
                <div>
                  <label htmlFor="stores-search" className="mb-1 block text-sm text-foreground-muted">
                    Поиск по адресу
                  </label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
                    <Input
                      id="stores-search"
                      type="search"
                      placeholder="Улица, дом, название магазина…"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setOnlyOpenNow(v => !v)}
                    className={cn(
                      'rounded-full border px-3 py-1 text-sm font-medium transition-colors',
                      onlyOpenNow
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-700'
                        : 'border-border bg-white text-foreground hover:bg-zinc-50'
                    )}
                    title="Фильтр по графику работы (если он указан у магазина)"
                  >
                    Работает сейчас
                  </button>
                  <button
                    type="button"
                    disabled
                    className="cursor-not-allowed rounded-full border border-border bg-white px-3 py-1 text-sm font-medium text-foreground-muted"
                    title="Скоро: признак парковки появится в карточке магазина"
                  >
                    Есть парковка
                  </button>
                  <button
                    type="button"
                    disabled
                    className="cursor-not-allowed rounded-full border border-border bg-white px-3 py-1 text-sm font-medium text-foreground-muted"
                    title="Скоро: признак сервисного центра появится в карточке магазина"
                  >
                    Сервисный центр
                  </button>
                </div>

                <div className="text-sm text-foreground-muted">
                  Показано: <strong className="text-foreground">{filteredStores.length}</strong> из{' '}
                  {stores.length}
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Блок 3. Карта + список */}
      <section ref={heroMapRef} className="px-4 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl max-md:px-0 sm:px-6 lg:px-8">
          <div className="mb-6 px-0 max-md:px-4">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Карта и адреса</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Выберите магазин в списке — карта подсветит точку. Нажмите на маркер, чтобы перейти к карточке.
            </p>
          </div>

          <div className="grid gap-5 max-md:grid-cols-1 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div className="max-md:px-0 md:rounded-3xl md:border md:border-border md:bg-white md:p-4 lg:p-5">
              <p className="mb-3 hidden text-sm font-semibold text-foreground md:block">Список магазинов</p>
              {sortedStores.length === 0 ? (
                <p className="text-sm text-foreground-muted">По заданным фильтрам ничего не найдено.</p>
              ) : (
                <ul
                  ref={listRef}
                  className="no-scrollbar flex max-md:max-h-none flex-col gap-3 overflow-y-auto pr-0 max-md:px-0 md:max-h-[520px] md:pr-1"
                >
                  {sortedStores.map(({ store, distanceKm }) => {
                    const open = isOpenNow(store);
                    return (
                      <li
                        key={store.id}
                        ref={el => {
                          storeItemRefs.current[store.id] = el;
                        }}
                      >
                        <article
                          role="button"
                          tabIndex={0}
                          className={cn(
                            'w-full cursor-pointer rounded-2xl border p-4 text-left transition-colors',
                            selectedStoreId === store.id
                              ? 'border-emerald-600 bg-emerald-50/40'
                              : 'border-border bg-card hover:border-emerald-600/40'
                          )}
                          onClick={() => {
                            if (store.slug) {
                              router.push(`/stores/${store.slug}`);
                              return;
                            }
                            setSelectedStoreId(store.id);
                          }}
                          onKeyDown={e => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              if (store.slug) {
                                router.push(`/stores/${store.slug}`);
                                return;
                              }
                              setSelectedStoreId(store.id);
                            }
                          }}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h3 className="truncate font-semibold text-foreground">{store.name}</h3>
                              <p className="mt-1 flex items-start gap-2 text-sm text-foreground-muted">
                                <MapPin className="mt-0.5 size-4 shrink-0" />
                                <span className="truncate">
                                  {store.city}, {store.address}
                                </span>
                              </p>
                              <p className="mt-1 flex items-start gap-2 text-sm text-foreground-muted">
                                <Clock className="mt-0.5 size-4 shrink-0" />
                                {formatWorkingHours(store.working_hours)}
                              </p>
                            </div>
                            <div className="shrink-0 text-right">
                              {distanceKm != null && (
                                <div className="text-sm font-semibold text-foreground">
                                  {distanceKm.toFixed(distanceKm < 10 ? 1 : 0)} км
                                </div>
                              )}
                              {open != null && (
                                <div
                                  className={cn(
                                    'mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold',
                                    open ? 'bg-emerald-50 text-emerald-700' : 'bg-zinc-100 text-zinc-600'
                                  )}
                                >
                                  {open ? 'Открыто' : 'Закрыто'}
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="mt-3 grid gap-2 sm:grid-cols-2">
                            {store.slug ? (
                              <Button
                                asChild
                                variant="secondary"
                                size="sm"
                                className="w-full sm:col-span-2"
                                onClick={e => e.stopPropagation()}
                              >
                                <Link href={`/stores/${store.slug}`}>О магазине</Link>
                              </Button>
                            ) : null}
                            <Button
                              asChild
                              variant="outline"
                              size="sm"
                              className="w-full"
                              onClick={e => e.stopPropagation()}
                            >
                              <a
                                href={buildYandexRouteUrl(store, userLocation ?? undefined)}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                Построить маршрут <Navigation className="ml-2 h-4 w-4" />
                              </a>
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              className="w-full"
                              onClick={e => {
                                e.stopPropagation();
                                document
                                  .getElementById('stores-stock-block')
                                  ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                setSelectedStoreId(store.id);
                              }}
                            >
                              Наличие товара <ShoppingBag className="ml-2 h-4 w-4" />
                            </Button>
                          </div>
                        </article>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="overflow-hidden max-md:rounded-2xl md:rounded-3xl md:border md:border-border md:bg-white">
              <StoresMapDynamic
                stores={filteredStores}
                selectedStoreId={selectedStoreId}
                onSelectStore={id => {
                  setSelectedStoreId(id);
                }}
              />
              <div className="border-t border-border p-4 text-sm text-foreground-muted">
                Подсказка: клик по маркеру выберет магазин в списке.
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Блок 4. Наличие товара */}
      <section id="stores-stock-block" className="px-2 py-10 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
              Проверить наличие товара в магазинах
            </h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Выберите товар — узнаете, где есть в наличии сегодня.
            </p>
          </div>

          <Card className="rounded-3xl border border-border bg-white p-4 sm:p-6">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
              <div className="relative">
                <label htmlFor="stores-product" className="mb-1 block text-sm text-foreground-muted">
                  Поиск товара
                </label>
                <Input
                  id="stores-product"
                  value={productQuery}
                  onChange={e => {
                    setProductQuery(e.target.value);
                    setShowAutocomplete(true);
                    setSelectedProduct(null);
                  }}
                  placeholder="Название, SKU или артикул…"
                  onFocus={() => setShowAutocomplete(true)}
                />

                {showAutocomplete && productQuery.trim().length >= 2 && (
                  <div
                    className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-border bg-white shadow-lg"
                    role="listbox"
                    aria-label="Подсказки товаров"
                  >
                    {autocompleteLoading ? (
                      <div className="p-3 text-sm text-foreground-muted">Поиск…</div>
                    ) : autocomplete.length === 0 ? (
                      <div className="p-3 text-sm text-foreground-muted">Ничего не найдено.</div>
                    ) : (
                      <ul className="max-h-[320px] overflow-y-auto">
                        {autocomplete.slice(0, 10).map(item => (
                          <li key={item.id}>
                            <button
                              type="button"
                              className="w-full px-3 py-2 text-left text-sm hover:bg-zinc-50"
                              onClick={() => {
                                setSelectedProduct(item);
                                setProductQuery(item.title);
                                setShowAutocomplete(false);
                              }}
                            >
                              <div className="flex items-center justify-between gap-3">
                                <span className="truncate font-medium text-foreground">{item.title}</span>
                                <span className="shrink-0 text-xs text-foreground-muted">{item.price} ₽</span>
                              </div>
                              {item.sku && (
                                <div className="mt-0.5 text-xs text-foreground-muted">SKU: {item.sku}</div>
                              )}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setProductQuery('');
                    setSelectedProduct(null);
                  }}
                  disabled={!productQuery && !selectedProduct}
                >
                  Очистить
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setShowAutocomplete(false)}
                  title="Скрыть список подсказок"
                >
                  Скрыть
                </Button>
              </div>
            </div>

            {selectedProduct && (
              <div className="mt-4 rounded-2xl border border-border bg-zinc-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-foreground">{selectedProduct.title}</p>
                    <p className="mt-1 text-xs text-foreground-muted">
                      {selectedProduct.sku ? `SKU: ${selectedProduct.sku}` : 'SKU: —'}
                    </p>
                  </div>
                  <div className="text-sm font-semibold text-foreground">{selectedProduct.price} ₽</div>
                </div>
              </div>
            )}

            {selectedProduct && (
              <div className="mt-6">
                <p className="mb-3 text-sm font-semibold text-foreground">Наличие по магазинам</p>
                {stockLoading ? (
                  <div className="flex min-h-[120px] items-center justify-center">
                    <Loading />
                  </div>
                ) : (
                  <div className="grid gap-3 lg:grid-cols-2">
                    {selectedProduct &&
                      storesForStock.length > 0 &&
                      !hasStockInFilteredStores && (
                        <div className="col-span-full rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
                          <p className="font-medium">Кнопка «Забрать в этом магазине» выключена намеренно.</p>
                          <p className="mt-1 text-amber-900/90">
                            По ответу API остатков для этого товара во всех показанных точках{' '}
                            <strong>доступное количество равно нулю</strong> (нет записи склада или всё
                            зарезервировано). Когда появится свободный остаток, бейдж покажет количество, и
                            кнопка станет активной.
                          </p>
                        </div>
                      )}
                    {storesForStock
                      .map(({ store, available }) => ({ store, available }))
                      .sort((a, b) => b.available - a.available)
                      .slice(0, 10)
                      .map(({ store, available }) => {
                        const open = isOpenNow(store);
                        const pickupToday = available > 0 && open !== false;
                        const pickupTomorrow = available > 0;
                        return (
                          <Card
                            key={store.id}
                            className={cn(
                              'rounded-2xl border border-border bg-white p-4',
                              selectedStoreId === store.id && 'ring-1 ring-emerald-600'
                            )}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="truncate text-sm font-semibold text-foreground">{store.name}</p>
                                <p className="mt-1 text-xs text-foreground-muted">
                                  {store.city}, {store.address}
                                </p>
                              </div>
                              <div
                                className={cn(
                                  'shrink-0 rounded-full px-2 py-1 text-xs font-semibold',
                                  available > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-zinc-100 text-zinc-600'
                                )}
                              >
                                {quantityLabel(available)}
                              </div>
                            </div>

                            <div className="mt-3 grid gap-2 text-sm">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-foreground-muted">Самовывоз сегодня</span>
                                <span className={cn('font-semibold', pickupToday ? 'text-emerald-700' : 'text-zinc-500')}>
                                  {pickupToday ? 'Да' : 'Нет'}
                                </span>
                              </div>
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-foreground-muted">Самовывоз завтра</span>
                                <span className={cn('font-semibold', pickupTomorrow ? 'text-emerald-700' : 'text-zinc-500')}>
                                  {pickupTomorrow ? 'Да' : 'Нет'}
                                </span>
                              </div>
                            </div>

                            <div className="mt-4 grid gap-2 sm:grid-cols-2">
                              <Button
                                asChild
                                variant="outline"
                                size="sm"
                                className="w-full"
                              >
                                <a
                                  href={buildYandexRouteUrl(store, userLocation ?? undefined)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Маршрут <ExternalLink className="ml-2 h-4 w-4" />
                                </a>
                              </Button>
                              <Button
                                size="sm"
                                className="w-full"
                                disabled={available <= 0 || addToCartMutation.isPending}
                                title={
                                  available <= 0
                                    ? 'Нет доступного остатка в этом магазине по данным API остатков (quantity − reserved).'
                                    : undefined
                                }
                                onClick={async () => {
                                  setSelectedStoreId(store.id);
                                  await addToCartMutation.mutateAsync({
                                    productId: selectedProduct.id,
                                    storeId: store.id,
                                  });
                                  await goToCheckoutPickup();
                                }}
                              >
                                Забрать в этом магазине <ShoppingBag className="ml-2 h-4 w-4" />
                              </Button>
                            </div>
                          </Card>
                        );
                      })}
                  </div>
                )}
              </div>
            )}

            {!selectedProduct && (
              <p className="mt-4 text-sm text-foreground-muted">
                Начните вводить название товара — появятся подсказки. Затем покажем наличие по магазинам.
              </p>
            )}
          </Card>
        </div>
      </section>

      {/* Блок 6. FAQ */}
      <section className="px-2 pb-12 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">FAQ по магазинам</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">
              Коротко отвечаем на частые вопросы.
            </p>
          </div>

          <div className="grid gap-3">
            {[
              {
                q: 'Можно ли вернуть товар в любой магазин?',
                a: 'Да, вы можете обратиться в любой магазин Ringoo с чеком/заказом. Детали зависят от категории товара и условий возврата.',
              },
              {
                q: 'Работают ли магазины в праздники?',
                a: 'Как правило — да, по обычному графику. В редких случаях расписание может меняться, актуальную информацию смотрите в карточке магазина.',
              },
              {
                q: 'Можно ли проверить технику перед оплатой?',
                a: 'Да. Мы поможем проверить комплектацию и базовую работоспособность товара до оплаты.',
              },
              {
                q: 'Можно ли забронировать товар для самовывоза?',
                a: 'Да — оформите заказ с самовывозом. Если товар в наличии, вы сможете забрать его сегодня.',
              },
            ].map(item => (
              <details
                key={item.q}
                className="group rounded-2xl border border-border bg-white p-4 open:shadow-sm"
              >
                <summary className="cursor-pointer list-none text-sm font-semibold text-foreground">
                  <span className="inline-flex items-center gap-2">
                    <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-50 text-emerald-700">
                      ?
                    </span>
                    {item.q}
                  </span>
                </summary>
                <p className="mt-3 text-sm text-foreground-muted">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

