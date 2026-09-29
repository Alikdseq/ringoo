'use client';

import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { usePrefersReducedMotion } from '@/lib/hooks/usePrefersReducedMotion';
import { TOUCH_TARGET_MOBILE_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  closeOnOverlayClick?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  closeOnOverlayClick = true,
}: ModalProps) {
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [isOpen, onClose]);

  const panelTransition = reducedMotion
    ? { duration: 0 }
    : { duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] as const };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm sm:items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reducedMotion ? 0 : 0.2 }}
          onClick={closeOnOverlayClick ? onClose : undefined}
          role="presentation"
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? 'modal-title' : undefined}
            className={cn(
              'relative mx-auto w-full max-w-lg border border-border bg-white shadow-xl',
              'max-h-[90dvh] overflow-y-auto rounded-t-2xl p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]',
              'sm:max-h-[85vh] sm:rounded-xl sm:mx-4'
            )}
            initial={reducedMotion ? false : { opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reducedMotion ? undefined : { opacity: 0, y: 16, scale: 0.98 }}
            transition={panelTransition}
            onClick={e => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'absolute right-3 top-3 inline-flex items-center justify-center rounded-lg text-foreground-muted hover:bg-zinc-100 hover:text-foreground active:bg-zinc-200',
                TOUCH_TARGET_MOBILE_CLASS
              )}
              aria-label="Закрыть"
            >
              <X className="h-5 w-5" />
            </button>
            {title && (
              <h2
                id="modal-title"
                className="mb-4 pr-12 text-lg font-semibold tracking-tight text-foreground"
              >
                {title}
              </h2>
            )}
            {!title && <div className="h-8 shrink-0" aria-hidden />}
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
