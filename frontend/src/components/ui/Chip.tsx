'use client';

import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

type ChipVariant = 'filter' | 'removable';

export interface ChipProps {
  children: React.ReactNode;
  variant?: ChipVariant;
  onRemove?: () => void;
  className?: string;
}

export function Chip({ children, variant = 'filter', onRemove, className }: ChipProps) {
  const isRemovable = variant === 'removable' && onRemove;

  return (
    <motion.span
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.15 }}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium',
        'bg-brand-soft text-brand-muted transition-colors duration-150',
        'hover:bg-brand hover:text-white',
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
          className="rounded-full p-0.5 transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
          aria-label="Удалить"
        >
          <X className="h-3.5 w-3.5" />
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
