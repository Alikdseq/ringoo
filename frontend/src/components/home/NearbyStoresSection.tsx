'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Navigation, Clock } from 'lucide-react';
import type { Store } from '@/types';
import { getStores } from '@/lib/api/services/stores.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';
import { cn } from '@/lib/theme/utils';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS } from '@/lib/theme/spacing';
import dynamic from 'next/dynamic';

const StoresMapDynamic = dynamic(
  () =>
    import('@/components/features/stores/StoresMap').then(m => ({
      default: m.StoresMap,
    })),
  {
    loading: () => <div className="h-[320px] w-full animate-pulse rounded-[32px] bg-zinc-100" />,
    ssr: false,
  }
);

type LatLon = { lat: number; lon: number };

const DAY_KEYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'] as const;

function parseCoords(store: Store): LatLon | null {
  if (!store.coordinates) return null;
  const lat = Number(store.coordinates.latitude);
  const lon = Number(store.coordinates.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return { lat, lon };
}

function haversineKm(a: LatLon, b: LatLon): number {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return 2 * R * Math.asin(Math.sqrt(s));
}

function getTodayHours(store: Store): string | null {
  const wh = store.working_hours;
  if (!wh) return null;
  const key = DAY_KEYS[new Date().getDay()];
  return wh[key] ?? null;
}

function buildYandexRouteUrl(store: Store): string {
  if (store.coordinates) {
    const lon = store.coordinates.longitude;
    const lat = store.coordinates.latitude;
    return `https://yandex.ru/maps/?pt=${lon},${lat}&z=16`;
  }
  const query = encodeURIComponent([store.city, store.address].filter(Boolean).join(', '));
  return `https://yandex.ru/maps/?text=${query}`;
}

export function NearbyStoresSection() {
  const home = useHomePageCopy();
  const ns = home.nearbyStores;
  const [userLocation, setUserLocation] = useState<LatLon | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoStatus, setGeoStatus] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['stores', 'home-nearby'],
    queryFn: () => getStores({ is_active: true }),
    staleTime: 5 * 60 * 1000,
  });

  const stores = useMemo(() => data?.results ?? [], [data?.results]);

  const storesWithDistance = useMemo(() => {
    if (!userLocation) return null;
    return stores
      .map(s => {
        const coords = parseCoords(s);
        if (!coords) return { store: s, km: null as number | null };
        return { store: s, km: haversineKm(userLocation, coords) };
      })
      .sort((a, b) => {
        if (a.km == null && b.km == null) return 0;
        if (a.km == null) return 1;
        if (b.km == null) return -1;
        return a.km - b.km;
      });
  }, [stores, userLocation]);

  const top3 = useMemo(() => {
    const list = storesWithDistance ?? stores.map(s => ({ store: s, km: null as number | null }));
    return list.slice(0, 3);
  }, [stores, storesWithDistance]);

  const handleDetectLocation = () => {
    setGeoError(null);
    setGeoStatus(null);
    if (!('geolocation' in navigator)) {
      setGeoError('Геолокация недоступна в этом браузере.');
      return;
    }
    // Для части браузеров геолокация работает только в secure context (HTTPS или localhost).
    if (typeof window !== 'undefined' && window.isSecureContext === false) {
      setGeoError('Геолокация работает только на HTTPS (или localhost).');
      return;
    }
    setGeoLoading(true);
    setGeoStatus('Запрашиваем доступ к геолокации…');

    const run = () =>
      navigator.geolocation.getCurrentPosition(
        pos => {
          setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
          setGeoLoading(false);
          setGeoStatus(null);
        },
        (err: GeolocationPositionError) => {
          const msg =
            err.code === err.PERMISSION_DENIED
              ? 'Доступ к геолокации запрещён в браузере. Разрешите доступ и попробуйте ещё раз.'
              : err.code === err.POSITION_UNAVAILABLE
                ? 'Не удалось получить координаты (позиция недоступна). Попробуйте позже.'
                : 'Слишком долго ждём ответ от геолокации. Попробуйте ещё раз.';
          setGeoError(msg);
          setGeoLoading(false);
          setGeoStatus(null);
        },
        { enableHighAccuracy: false, timeout: 12_000, maximumAge: 60_000 }
      );

    // Поддержка Permissions API: можем аккуратно объяснить статус до запроса.
    const permissions = (navigator as unknown as { permissions?: any }).permissions;
    if (permissions?.query) {
      permissions
        .query({ name: 'geolocation' })
        .then((res: { state: 'granted' | 'prompt' | 'denied' }) => {
          if (res.state === 'denied') {
            setGeoError(
              'Геолокация заблокирована в настройках сайта. Разрешите доступ в адресной строке и повторите.'
            );
            setGeoLoading(false);
            setGeoStatus(null);
            return;
          }
          run();
        })
        .catch(run);
    } else {
      run();
    }
  };

  const errorText = isError ? getFriendlyErrorMessage(error) : null;

  return (
    <section className={HOME_SECTION_CLASS}>
      <div className={HOME_SECTION_INNER_CLASS}>
        <div className="mb-6 flex flex-col gap-4 max-md:items-stretch md:flex-row md:items-end md:justify-between">
          <div className="min-w-0">
            <h2 className="text-2xl font-semibold leading-tight tracking-tight text-foreground sm:text-3xl">
              {ns.title}
            </h2>
            <p className="mt-2 max-w-none text-sm text-foreground-muted sm:text-base">
              {ns.subtitle}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 max-md:w-full md:shrink-0 md:justify-end">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="max-md:flex-1 sm:max-md:flex-none"
              onClick={handleDetectLocation}
              loading={geoLoading}
            >
              <Navigation className="mr-2 h-4 w-4 shrink-0" />
              {ns.detectLocation}
            </Button>
            <Button asChild variant="secondary" size="sm" className="max-md:flex-1 sm:max-md:flex-none">
              <Link href="/stores">{ns.allStores}</Link>
            </Button>
          </div>
        </div>

        {geoError && (
          <div className="mb-4 rounded-2xl border border-border bg-white px-5 py-3 text-sm text-foreground-muted">
            {geoError}
          </div>
        )}
        {geoStatus && (
          <div className="mb-4 rounded-2xl border border-border bg-white px-5 py-3 text-sm text-foreground-muted">
            {geoStatus}
          </div>
        )}

        {isLoading ? (
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="h-[320px] animate-pulse rounded-[32px] border border-border bg-zinc-100" />
            <div className="space-y-3">
              <div className="h-[98px] animate-pulse rounded-[28px] border border-border bg-zinc-100" />
              <div className="h-[98px] animate-pulse rounded-[28px] border border-border bg-zinc-100" />
              <div className="h-[98px] animate-pulse rounded-[28px] border border-border bg-zinc-100" />
            </div>
          </div>
        ) : errorText ? (
          <div className="rounded-2xl border border-border bg-white p-6 text-sm text-foreground-muted">
            {errorText}
          </div>
        ) : stores.length === 0 ? (
          <div className="rounded-2xl border border-border bg-white p-6 text-sm text-foreground-muted">
            Сейчас нет активных магазинов для отображения.
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            {/* Yandex map with all store markers */}
            <Card className="relative overflow-hidden rounded-[32px] border border-border bg-white p-0">
              <StoresMapDynamic stores={stores} />
            </Card>

            {/* List of 3 nearest */}
            <div className="space-y-3">
              {top3.map(({ store, km }) => {
                const today = getTodayHours(store);
                return (
                  <Card
                    key={store.id}
                    className={cn(
                      'rounded-[28px] border border-border bg-white p-5',
                      'transition-shadow hover:shadow-md'
                    )}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground">{store.name}</p>
                        <p className="mt-1 flex items-start gap-2 text-sm text-foreground-muted">
                          <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
                          <span className="line-clamp-2">
                            {store.city}, {store.address}
                          </span>
                        </p>
                        {today && (
                          <p className="mt-2 flex items-center gap-2 text-sm text-foreground-muted">
                            <Clock className="h-4 w-4 shrink-0" />
                            <span>{today}</span>
                          </p>
                        )}
                      </div>
                      <div className="shrink-0 text-right">
                        {km != null ? (
                          <p className="text-sm font-semibold text-foreground">
                            {km < 1 ? `${Math.round(km * 1000)} м` : `${km.toFixed(1)} км`}
                          </p>
                        ) : (
                          <p className="text-sm font-semibold text-foreground">—</p>
                        )}
                        <a
                          href={buildYandexRouteUrl(store)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 inline-flex text-sm font-medium text-brand hover:underline"
                        >
                          {ns.route}
                        </a>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

