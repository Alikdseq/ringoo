'use client';

import type { Store } from '@/types';
import { StoresYandexMap } from '@/components/features/stores/StoresYandexMap';

interface StoresMapProps {
  stores: Store[];
  selectedStoreId?: string | null;
  onSelectStore?: (storeId: string) => void;
  heightClass?: string;
}

/** Совместимость со старым импортом — делегирует на StoresYandexMap. */
export function StoresMap({ stores, selectedStoreId, onSelectStore, heightClass }: StoresMapProps) {
  return (
    <StoresYandexMap
      stores={stores}
      selectedStoreId={selectedStoreId}
      onSelectStore={onSelectStore}
      heightClass={heightClass ?? 'h-80'}
    />
  );
}
