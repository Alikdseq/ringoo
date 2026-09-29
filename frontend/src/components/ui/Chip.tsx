'use client';

import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { usePrefersReducedMotion } from '@/lib/hooks/usePrefersReducedMotion';
import { TOUCH_TARGET_MOBILE_CLASS } from '@/lib/theme/spacing';

type ChipVariant = 'filter' | 'removable';

export interface ChipProps {
  children: React.ReactNode;
  variant?: ChipVariant;
  onRemove?: () => void;
  className?: string;
}

export function Chip({ children, variant = 'filter', onRemove, className }: ChipProps) {
  const reducedMotion = usePrefersReducedMotion();
  const isRemovable = variant === 'removable' && onRemove;

  return (
    <motion.span
      layout={!reducedMotion}
      initial={reducedMotion ? false : { opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={reducedMotion ? undefined : { opacity: 0, scale: 0.9 }}
      transition={{ duration: reducedMotion ? 0 : 0.15 }}
      className={clsx(
        'inline-flex min-h-[36px] items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium touch-manipulation sm:min-h-0',
        'bg-brand-soft text-brand-muted transition-colors duration-150',
        'hover:bg-brand hover:text-white active:bg-brand active:text-white',
        isRemovable && 'pr-1.5',
        className
      )}
    >
      {children}
      {isRemovable && (
        <button
          type="button"
          onClick={e => {
            e.stopPropagation();
            onRemove?.();
          }}
          className={clsx(
            'inline-flex items-center justify-center rounded-full transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 active:bg-white/30',
            TOUCH_TARGET_MOBILE_CLASS
          )}
          aria-label="Удалить"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </motion.span>
  );
}

export function ChipList({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx('flex flex-wrap items-center gap-2', className)}>
      <AnimatePresence mode="popLayout">{children}</AnimatePresence>
    </div>
  );
}
