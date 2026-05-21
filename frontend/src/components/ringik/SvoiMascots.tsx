'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/theme/utils';
import type { RingikProps } from '@/components/ringik/ringik-types';

/**
 * Свойский режим: бабушка Зина и дедушка Бола (плейсхолдер до отдельной спеки с ассетами).
 */
export function SvoiMascots({
  message,
  placement,
  className,
  bubbleAlign = 'center',
  bubblePlacement = 'top',
  onClick,
  clickable,
  visible = true,
  showMessage = false,
}: RingikProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className={cn(
            'z-[90]',
            placement === 'fixed-bottom-right'
              ? 'fixed bottom-5 right-5'
              : placement === 'fixed-top-right'
                ? 'fixed right-0 top-0'
                : 'absolute',
            'pointer-events-none',
            className
          )}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        >
          {showMessage && message && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 4 }}
              transition={{ duration: 0.18 }}
              className={cn(
                'absolute',
                bubblePlacement === 'top' && '-top-3 -translate-y-full',
                bubblePlacement === 'left' &&
                  'left-0 top-1/2 -translate-x-full -translate-y-1/2',
                bubblePlacement === 'right' &&
                  'right-0 top-1/2 translate-x-full -translate-y-1/2',
                bubblePlacement === 'top' &&
                  (bubbleAlign === 'center'
                    ? 'left-1/2 -translate-x-1/2'
                    : bubbleAlign === 'left'
                      ? 'left-0 -translate-x-1/4'
                      : 'right-0 translate-x-1/4'),
                'max-w-[240px] rounded-2xl border border-amber-200/90 bg-amber-50 px-3 py-2 text-center text-xs font-medium text-amber-950 shadow-sm',
                'sm:text-sm'
              )}
            >
              {message}
            </motion.div>
          )}

          <button
            type="button"
            className={cn(
              'pointer-events-auto flex shrink-0 select-none items-end gap-1 border-0 bg-transparent p-0',
              placement === 'fixed-bottom-right' && 'drop-shadow-sm',
              clickable ? 'cursor-pointer' : 'cursor-default'
            )}
            onClick={clickable ? onClick : undefined}
            aria-label="Открыть помощник Зина и Бола"
            tabIndex={clickable ? 0 : -1}
          >
            <div className="flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-full border-2 border-amber-300 bg-gradient-to-br from-amber-100 to-amber-200 text-sm font-bold text-amber-950 sm:h-[60px] sm:w-[60px] sm:text-base">
              З
            </div>
            <div className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-full border-2 border-amber-400/80 bg-gradient-to-br from-amber-200 to-amber-300 text-sm font-bold text-amber-950 sm:h-[54px] sm:w-[54px] sm:text-base">
              Б
            </div>
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
