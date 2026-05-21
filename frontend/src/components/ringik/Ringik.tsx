'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Image from 'next/image';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { cn } from '@/lib/theme/utils';
import type { RingikPose, RingikProps } from '@/components/ringik/ringik-types';
import { SvoiMascots } from '@/components/ringik/SvoiMascots';
import { RINGIK_ENABLED } from '@/lib/ringik/featureFlags';

export type { RingikPose, RingikProps, RingikPlacement } from '@/components/ringik/ringik-types';

const RINGIK_ASSET_BY_POSE: Record<RingikPose, string> = {
  neutral: '/ringik/neutral.png',
  peeking: '/ringik/peeking.png',
  waving: '/ringik/waving.png',
  sitting: '/ringik/sitting.png',
  pointing: '/ringik/pointing.png',
  sad: '/ringik/sad.png',
  hiding: '/ringik/hiding.png',
  surprised: '/ringik/surprised.png',
  gift: '/ringik/gift.png',
  phone: '/ringik/phone.png',
};

function RingikRobot({
  pose,
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
  const src = RINGIK_ASSET_BY_POSE[pose];
  const isLcpCandidate =
    placement === 'fixed-bottom-right' || pose === 'peeking' || src.includes('peeking');

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className={cn(
            'z-[90]',
            placement === 'fixed-bottom-right'
              ? 'fixed bottom-6 right-4 sm:bottom-8 sm:right-5'
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
                'max-w-[220px] rounded-2xl border border-border bg-white px-3 py-2 text-center text-xs font-medium text-foreground shadow-sm',
                'sm:text-sm'
              )}
            >
              {message}
            </motion.div>
          )}

          <button
            type="button"
            className={cn(
              'pointer-events-auto shrink-0 border-0 bg-transparent p-0',
              clickable ? 'cursor-pointer' : 'cursor-default',
              placement === 'fixed-bottom-right'
                ? 'relative flex h-16 w-16 items-end justify-center sm:h-[4.5rem] sm:w-[4.5rem]'
                : 'relative flex h-[70px] w-[70px] items-end justify-center sm:h-[90px] sm:w-[90px]'
            )}
            onClick={clickable ? onClick : undefined}
            aria-label="Открыть помощник Рингик"
            tabIndex={clickable ? 0 : -1}
          >
            <Image
              src={src}
              alt=""
              width={200}
              height={200}
              priority={isLcpCandidate}
              className={cn(
                'pointer-events-none select-none object-contain object-bottom',
                placement === 'fixed-bottom-right'
                  ? 'h-[60px] w-[60px] drop-shadow-sm sm:h-[68px] sm:w-[68px]'
                  : 'h-auto w-[70px] sm:w-[90px]'
              )}
            />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function Ringik(props: RingikProps) {
  const { mode } = useUiMode();
  if (!RINGIK_ENABLED) return null;
  if (mode === 'svoi') {
    return <SvoiMascots {...props} />;
  }
  return <RingikRobot {...props} />;
}

function hasSessionMark(key: string) {
  const g = globalThis as unknown as { __ringik_seen__?: Record<string, true> };
  return Boolean(g.__ringik_seen__?.[key]);
}

function markSession(key: string) {
  const g = globalThis as unknown as { __ringik_seen__?: Record<string, true> };
  if (!g.__ringik_seen__) g.__ringik_seen__ = {};
  g.__ringik_seen__[key] = true;
}

export function useRingikIntersectionTrigger(
  ref: React.RefObject<HTMLElement | null>,
  onceKey: string,
  opts?: { bubbleMs?: number; visibleMs?: number; threshold?: number; rootMargin?: string }
) {
  const disabled = !RINGIK_ENABLED;
  const bubbleMs = opts?.bubbleMs ?? 4000;
  const visibleMs = opts?.visibleMs ?? 5000;
  const threshold = opts?.threshold ?? 0.5;
  const rootMargin = opts?.rootMargin ?? '0px';

  const [visible, setVisible] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const timersRef = useRef<number[]>([]);
  const triggeredRef = useRef(false);

  useEffect(() => {
    if (disabled) return;
    const el = ref.current;
    if (!el) return;
    if (triggeredRef.current) return;
    if (hasSessionMark(onceKey)) return;

    const obs = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        if (triggeredRef.current) return;
        triggeredRef.current = true;
        markSession(onceKey);

        setVisible(true);
        setShowMessage(true);

        timersRef.current.push(window.setTimeout(() => setShowMessage(false), bubbleMs));
        timersRef.current.push(window.setTimeout(() => setVisible(false), visibleMs));
      },
      { threshold, rootMargin }
    );
    obs.observe(el);
    return () => {
      obs.disconnect();
      timersRef.current.forEach(t => window.clearTimeout(t));
      timersRef.current = [];
    };
  }, [bubbleMs, disabled, onceKey, ref, rootMargin, threshold, visibleMs]);

  if (disabled) {
    return { visible: false, showMessage: false };
  }

  return { visible, showMessage };
}
