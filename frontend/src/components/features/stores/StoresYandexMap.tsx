'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { Store } from '@/types';
import { getStores } from '@/lib/api/services/stores.service';
import { YandexMap, type YandexMapMarker } from '@/components/features/maps/YandexMap';

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

function buildBalloon(store: Store): string {
  const addr = [store.city, store.address].filter(Boolean).join(', ');
  const phoneHtml = store.phone
    ? `<div style="margin-top:6px"><b>Телефон:</b> <a href="tel:${store.phone}">${store.phone}</a></div>`
    : '';
  const routeHref = store.coordinates
    ? `https://yandex.ru/maps/?pt=${store.coordinates.longitude},${store.coordinates.latitude}&z=16`
    : `https://yandex.ru/maps/?text=${encodeURIComponent(addr)}`;
  return [
    `<div style="font-size:13px;line-height:1.4;max-width:260px">`,
    `<div><b>Адрес:</b> ${addr}</div>`,
    `<div style="margin-top:6px"><b>График:</b> ${formatWorkingHours(store.working_hours)}</div>`,
    phoneHtml,
    `<div style="margin-top:8px"><a href="${routeHref}" target="_blank" rel="noopener noreferrer" style="color:#16a34a;font-weight:600">Маршрут в Яндекс.Картах →</a></div>`,
    `</div>`,
  ].join('');
}

function storeToMarker(store: Store, selectedId?: string | null): YandexMapMarker | null {
  if (!store.coordinates) return null;
  const lat = Number(store.coordinates.latitude);
  const lon = Number(store.coordinates.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return {
    id: store.id,
    coordinates: [lat, lon],
    title: store.name,
    description: buildBalloon(store),
    selected: selectedId === store.id,
  };
}

interface StoresYandexMapProps {
  /** Если не передан — компонент сам подгрузит все активные магазины. */
  stores?: Store[];
  selectedStoreId?: string | null;
  onSelectStore?: (storeId: string) => void;
  heightClass?: string;
  className?: string;
  zoom?: number;
  center?: [number, number];
}

/** Единый компонент карты со всеми магазинами Ringoo (используется на главной, /stores, /#delivery-payment и т.д.). */
export function StoresYandexMap({
  stores: storesProp,
  selectedStoreId,
  onSelectStore,
  heightClass,
  className,
  zoom,
  center,
}: StoresYandexMapProps) {
  const { data } = useQuery({
    queryKey: ['stores', 'map-all'],
    queryFn: () => getStores({ is_active: true }),
    staleTime: 5 * 60 * 1000,
    enabled: !storesProp,
  });

  const stores: Store[] = storesProp ?? data?.results ?? [];

  const markers = useMemo(() => {
    return stores
      .map(s => storeToMarker(s, selectedStoreId))
      .filter((m): m is YandexMapMarker => Boolean(m));
  }, [stores, selectedStoreId]);

  return (
    <YandexMap
      markers={markers}
      center={center}
      zoom={zoom ?? 12}
      heightClass={heightClass}
      className={className}
      onMarkerClick={onSelectStore}
    />
  );
}
