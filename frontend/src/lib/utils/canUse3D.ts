'use client';

import { useState, useEffect } from 'react';

/**
 * DESIGN_SPEC §6: определение возможностей 3D
 * Используется для выбора 3D-рендера или fallback (изображение/видео)
 */

/**
 * Проверяет, можно ли использовать 3D-эффекты.
 * - prefers-reduced-motion: reduce — отключаем 3D
 * - hardwareConcurrency <= 4 — слабый CPU, fallback
 * - SSR: всегда false (только на клиенте)
 */
export function canUse3D(): boolean {
  if (typeof window === 'undefined') return false;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return false;

  const cores = navigator.hardwareConcurrency ?? 4;
  if (cores <= 4) return false;

  return true;
}

/** Hook для клиентской проверки (избегаем hydration mismatch) */
export function useCanUse3D(): boolean {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- после SSR выставляем реальную поддержку 3D
    setOk(canUse3D());
  }, []);
  return ok;
}

/**
 * Проверяет, можно ли использовать 3D tilt (perspective transform).
 * Отключаем на touch-устройствах для стабильности.
 */
export function canUse3DTilt(): boolean {
  if (typeof window === 'undefined') return false;

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return false;

  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  if (hasTouch) return false;

  return true;
}

/** Hook для 3D tilt (избегаем hydration mismatch) */
export function useCanUse3DTilt(): boolean {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- после SSR выставляем поддержку tilt
    setOk(canUse3DTilt());
  }, []);
  return ok;
}
