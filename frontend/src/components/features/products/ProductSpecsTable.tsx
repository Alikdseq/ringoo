'use client';

import type { ProductDetail, ProductSpec } from '@/types';

interface ProductSpecsTableProps {
  product: ProductDetail;
}

export function ProductSpecsTable({ product }: ProductSpecsTableProps) {
  const specs: ProductSpec[] = product.specs ?? [];

  if (specs.length === 0) {
    return null;
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-lg font-semibold text-foreground">Характеристики</h2>
      <div className="overflow-hidden rounded-2xl border border-border bg-white">
        <dl className="divide-y divide-border text-sm">
          {specs.map(spec => (
            <div
              key={`${spec.name}-${spec.value}`}
              className="grid grid-cols-1 gap-1 px-4 py-3 odd:bg-[#f7f7f7] sm:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
            >
              <dt className="font-medium text-foreground-muted">{spec.name}</dt>
              <dd className="text-foreground">{spec.value}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
