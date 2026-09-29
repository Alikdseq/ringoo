'use client';

import { Building2, Heart } from 'lucide-react';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { UI_MODE_SVOI_ENABLED } from '@/lib/ui-mode/featureFlags';
import { cn } from '@/lib/theme/utils';

type Variant = 'header' | 'header-compact' | 'mobile' | 'mobile-menu';

export function UiModeToggle({ variant = 'header' }: { variant?: Variant }) {
  const { mode, setMode } = useUiMode();

  if (!UI_MODE_SVOI_ENABLED) {
    return null;
  }
  const isSvoi = mode === 'svoi';

  const baseBtn =
    'inline-flex touch-manipulation items-center justify-center rounded-full border-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand)] focus-visible:ring-offset-2';

  if (variant === 'header-compact') {
    return (
      <div
        className="flex shrink-0 items-center lg:hidden"
        role="group"
        aria-label="Режим оформления сайта"
      >
        <button
          type="button"
          onClick={() => setMode('official')}
          title="Официальный режим"
          aria-pressed={!isSvoi}
          className={cn(
            baseBtn,
            'h-11 w-11 rounded-r-none border-r-0',
            !isSvoi
              ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-[var(--color-brand-muted)]'
              : 'border-border bg-white text-foreground-muted'
          )}
        >
          <Building2 className="h-5 w-5" aria-hidden />
          <span className="sr-only">Официальный</span>
        </button>
        <button
          type="button"
          onClick={() => setMode('svoi')}
          title="Свойский режим"
          aria-pressed={isSvoi}
          className={cn(
            baseBtn,
            'h-11 w-11 rounded-l-none border-l-0',
            isSvoi
              ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-[var(--color-brand-muted)]'
              : 'border-border bg-white text-foreground-muted'
          )}
        >
          <Heart className="h-5 w-5" aria-hidden />
          <span className="sr-only">Свойский</span>
        </button>
      </div>
    );
  }

  if (variant === 'mobile' || variant === 'mobile-menu') {
    const shellClass =
      variant === 'mobile-menu'
        ? 'mb-2 rounded-xl border border-border/50 bg-transparent px-1 py-2'
        : 'mb-2 rounded-xl border border-border/80 bg-white/95 px-3 py-2.5 shadow-sm backdrop-blur-sm';
    return (
      <div className={shellClass} role="group" aria-label="Режим оформления сайта">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMode('official')}
            title="Официальный режим"
            aria-pressed={!isSvoi}
            className={cn(
              baseBtn,
              'min-h-11 min-w-11 flex-1 gap-1.5 px-2 py-2 text-xs font-semibold',
              !isSvoi
                ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-foreground'
                : 'border-border bg-white text-foreground-muted hover:bg-zinc-50'
            )}
          >
            <Building2 className="h-5 w-5 shrink-0" aria-hidden />
            <span className="truncate">Официальный</span>
          </button>
          <button
            type="button"
            onClick={() => setMode('svoi')}
            title="Свойский режим"
            aria-pressed={isSvoi}
            className={cn(
              baseBtn,
              'min-h-11 min-w-11 flex-1 gap-1.5 px-2 py-2 text-xs font-semibold',
              isSvoi
                ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-foreground'
                : 'border-border bg-white text-foreground-muted hover:bg-zinc-50'
            )}
          >
            <Heart className="h-5 w-5 shrink-0" aria-hidden />
            <span className="truncate">Свойский</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="hidden items-center lg:flex"
      role="group"
      aria-label="Режим оформления сайта"
    >
      <button
        type="button"
        onClick={() => setMode('official')}
        title="Официальный режим"
        aria-pressed={!isSvoi}
        className={cn(
          baseBtn,
          'h-11 w-11 border-r-0 rounded-r-none',
          !isSvoi
            ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-[var(--color-brand-muted)]'
            : 'border-border bg-white text-foreground-muted hover:bg-zinc-100'
        )}
      >
        <Building2 className="mx-auto h-5 w-5" aria-hidden />
        <span className="sr-only">Официальный режим</span>
      </button>
      <button
        type="button"
        onClick={() => setMode('svoi')}
        title="Свойский режим"
        aria-pressed={isSvoi}
        className={cn(
          baseBtn,
          'h-11 w-11 rounded-l-none border-l-0',
          isSvoi
            ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-[var(--color-brand-muted)]'
            : 'border-border bg-white text-foreground-muted hover:bg-zinc-100'
        )}
      >
        <Heart className="mx-auto h-5 w-5" aria-hidden />
        <span className="sr-only">Свойский режим</span>
      </button>
    </div>
  );
}
