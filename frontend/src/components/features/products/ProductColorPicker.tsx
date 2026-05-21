'use client';

import { cn } from '@/lib/theme/utils';
import { mergeColorGroups, resolveColorSwatchHex, type MergedColorGroup } from '@/lib/product-colors';
import type { ProductDetail } from '@/types';
import { useMemo } from 'react';

interface ProductColorPickerProps {
  product: ProductDetail;
  selectedGroupKey: string | null;
  onSelectGroupKey: (key: string) => void;
}

export function ProductColorPicker({
  product,
  selectedGroupKey,
  onSelectGroupKey,
}: ProductColorPickerProps) {
  const colorGroups = useMemo(
    () => mergeColorGroups(product.colors ?? []),
    [product.colors]
  );

  if (colorGroups.length === 0) return null;

  return (
    <div className="min-w-0 flex-1">
      <p className="text-xs uppercase tracking-wide text-foreground-muted">Цвет</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {colorGroups.map((g: MergedColorGroup) => {
          const active = g.key === selectedGroupKey;
          const fill = resolveColorSwatchHex(g);
          return (
            <button
              key={g.key}
              type="button"
              onClick={() => onSelectGroupKey(g.key)}
              className={cn(
                'flex max-w-[10rem] items-center gap-2 rounded-full border px-2.5 py-1.5 text-left text-sm transition-colors',
                active
                  ? 'border-zinc-900 bg-white text-foreground'
                  : 'border-border bg-white text-foreground-muted hover:border-zinc-300'
              )}
              aria-pressed={active}
            >
              <span
                className="h-7 w-7 shrink-0 rounded-full border-2 border-white shadow ring-1 ring-black/10"
                style={{ backgroundColor: fill }}
                aria-hidden
              />
              <span className="min-w-0 truncate leading-tight">{g.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
