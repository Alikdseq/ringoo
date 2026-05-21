'use client';

import type { ProductDetail } from '@/types';
import { ProductGallery } from './ProductGallery';

interface ProductMediaAreaProps {
  product: ProductDetail;
  selectedGroupKey: string | null;
  onActiveColorIdChange?: (colorId: string | null) => void;
}

/** PDP: только галерея фото (3D временно отключён). */
export function ProductMediaArea({
  product,
  selectedGroupKey,
  onActiveColorIdChange,
}: ProductMediaAreaProps) {
  return (
    <div className="min-w-0 max-w-full space-y-3">
      <ProductGallery
        product={product}
        selectedGroupKey={selectedGroupKey}
        onActiveColorIdChange={onActiveColorIdChange}
      />
    </div>
  );
}
