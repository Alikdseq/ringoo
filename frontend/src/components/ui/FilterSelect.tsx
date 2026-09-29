import type { SelectHTMLAttributes, ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/theme/utils';

export interface FilterSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  labelClassName?: string;
  wrapperClassName?: string;
  children: ReactNode;
}

export function FilterSelect({
  label,
  labelClassName,
  wrapperClassName,
  className,
  id,
  children,
  ...props
}: FilterSelectProps) {
  const selectId = id ?? (label ? label.replace(/\s+/g, '-').toLowerCase() : undefined);

  return (
    <div className={cn('space-y-1', wrapperClassName)}>
      {label ? (
        <label
          htmlFor={selectId}
          className={cn('block text-sm font-medium text-foreground-muted', labelClassName)}
        >
          {label}
        </label>
      ) : null}
      <div className="relative">
        <select
          id={selectId}
          className={cn(
            'w-full min-h-[44px] appearance-none rounded-xl border border-border bg-white',
            'px-3 py-2.5 pr-10 text-base text-foreground touch-manipulation sm:text-sm',
            'transition-colors duration-150',
            'focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-1',
            'disabled:cursor-not-allowed disabled:opacity-60',
            className
          )}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted"
          aria-hidden
        />
      </div>
    </div>
  );
}
