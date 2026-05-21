'use client';

import type { Store } from '@/types';
import { YandexMap } from '@/components/features/maps/YandexMap';

interface StoresMapProps {
  stores: Store[];
  selectedStoreId?: string | null;
  onSelectStore?: (storeId: string) => void;
}

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

export function StoresMap({ stores, selectedStoreId, onSelectStore }: StoresMapProps) {
  const markers = stores
    .filter(store => store.coordinates)
    .map(store => ({
      id: store.id,
      coordinates: [Number(store.coordinates!.latitude), Number(store.coordinates!.longitude)] as [
        number,
        number,
      ],
      title: store.name,
      description: [
        `<div style="font-size:13px;line-height:1.35">`,
        `<div style="margin-bottom:6px"><b>Адрес:</b> ${[store.city, store.address]
          .filter(Boolean)
          .join(', ')}</div>`,
        `<div style="margin-bottom:6px"><b>График:</b> ${formatWorkingHours(
          store.working_hours
        )}</div>`,
        store.phone
          ? `<div><b>Телефон:</b> <a href="tel:${store.phone}">${store.phone}</a></div>`
          : `<div><b>Телефон:</b> —</div>`,
        `</div>`,
      ].join(''),
      selected: selectedStoreId === store.id,
    }));

  return (
    <YandexMap
      markers={markers}
      center={[43.0246, 44.6818]}
      zoom={12}
      className="h-80"
      onMarkerClick={onSelectStore}
    />
  );
}
