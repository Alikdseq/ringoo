'use client';

import { useMemo, useState } from 'react';
import type { Store } from '@/types';
import { StoresMap } from '@/components/features/stores/StoresMap';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/theme/utils';

/** Расстояние между двумя точками в км (формула Хаверсина). */
function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export type StoreSort = 'default' | 'distance';

export interface StoreSelectorProps {
  stores: Store[];
  selectedStoreId: string | null;
  onSelectStore: (storeId: string) => void;
  error?: string;
  /** Заголовок над списком (по умолчанию "Выберите магазин") */
  listTitle?: string;
  /** Заголовок над картой (по умолчанию "Магазины на карте") */
  mapTitle?: string;
}

export function StoreSelector({
  stores,
  selectedStoreId,
  onSelectStore,
  error,
  listTitle = 'Выберите магазин',
  mapTitle = 'Магазины на карте',
}: StoreSelectorProps) {
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<StoreSort>('default');

  const filteredAndSortedStores = useMemo(() => {
    const query = search.trim().toLowerCase();
    let list = query
      ? stores.filter(
          s =>
            s.name.toLowerCase().includes(query) ||
            s.city.toLowerCase().includes(query) ||
            s.address.toLowerCase().includes(query)
        )
      : [...stores];

    if (sort === 'distance') {
      const withCoords = list.filter(s => s.coordinates);
      const withoutCoords = list.filter(s => !s.coordinates);
      if (withCoords.length === 0) return list;
      const centerLat =
        withCoords.reduce((sum, s) => sum + Number(s.coordinates!.latitude), 0) / withCoords.length;
      const centerLon =
        withCoords.reduce((sum, s) => sum + Number(s.coordinates!.longitude), 0) /
        withCoords.length;
      withCoords.sort((a, b) => {
        const distA = haversineKm(
          centerLat,
          centerLon,
          Number(a.coordinates!.latitude),
          Number(a.coordinates!.longitude)
        );
        const distB = haversineKm(
          centerLat,
          centerLon,
          Number(b.coordinates!.latitude),
          Number(b.coordinates!.longitude)
        );
        return distA - distB;
      });
      list = [...withCoords, ...withoutCoords];
    } else {
      list.sort((a, b) => a.name.localeCompare(b.name));
    }

    return list;
  }, [stores, search, sort]);

  if (stores.length === 0) {
    return (
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Нет доступных магазинов для самовывоза.
      </p>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div>
        <h3 className="mb-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">{listTitle}</h3>
        <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            type="search"
            placeholder="Поиск по городу или адресу..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="min-w-0 flex-1"
          />
          <select
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            value={sort}
            onChange={e => setSort(e.target.value as StoreSort)}
            aria-label="Сортировка магазинов"
          >
            <option value="default">По названию</option>
            <option value="distance">По расстоянию</option>
          </select>
        </div>
        <div className="max-h-64 overflow-y-auto rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          <ul className="divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
            {filteredAndSortedStores.map(store => (
              <li
                key={store.id}
                role="button"
                tabIndex={0}
                className={cn(
                  'cursor-pointer px-4 py-3 transition-colors',
                  selectedStoreId === store.id
                    ? 'bg-zinc-100 dark:bg-zinc-900'
                    : 'hover:bg-zinc-50 dark:hover:bg-zinc-900/60'
                )}
                onClick={() => onSelectStore(store.id)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectStore(store.id);
                  }
                }}
              >
                <p className="font-medium text-zinc-900 dark:text-zinc-50">{store.name}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {store.city}, {store.address}
                </p>
              </li>
            ))}
          </ul>
        </div>
        {filteredAndSortedStores.length === 0 && (
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
            По запросу ничего не найдено.
          </p>
        )}
        {error && <p className="mt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
      </div>
      <div>
        <h3 className="mb-2 text-sm font-medium text-zinc-700 dark:text-zinc-300">{mapTitle}</h3>
        <StoresMap
          stores={filteredAndSortedStores}
          selectedStoreId={selectedStoreId}
          onSelectStore={onSelectStore}
        />
      </div>
    </div>
  );
}
