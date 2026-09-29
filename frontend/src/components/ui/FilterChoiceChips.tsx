'use client';

import { cn } from '@/lib/theme/utils';

export type FilterChoiceOption = {
  value: string;
  label: string;
};

export interface FilterChoiceChipsProps {
  options: FilterChoiceOption[];
  value: string;
  onChange: (value: string) => void;
  allLabel?: string;
  className?: string;
}

function chipButtonClass(active: boolean) {
  return cn(
    'inline-flex min-h-[40px] shrink-0 items-center justify-center rounded-full border px-3.5 py-2 text-sm font-medium touch-manipulation transition-all duration-150',
    active
      ? 'border-[var(--color-brand)] bg-[var(--color-brand)] text-white shadow-[0_0_0_1px_rgba(34,197,94,0.25)]'
      : 'border-border bg-white text-foreground hover:border-[var(--color-brand)]/40 hover:bg-[var(--color-brand-soft)]'
  );
}

export function FilterChoiceChips({
  options,
  value,
  onChange,
  allLabel = 'Все',
  className,
}: FilterChoiceChipsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)} role="group">
      <button type="button" className={chipButtonClass(value === '')} onClick={() => onChange('')}>
        {allLabel}
      </button>
      {options.map(opt => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value || opt.label}
            type="button"
            className={chipButtonClass(active)}
            onClick={() => onChange(active ? '' : opt.value)}
            aria-pressed={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
