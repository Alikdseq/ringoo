'use client';

import { useEffect, useState } from 'react';

function formatRemaining(endMs: number): string {
  const now = Date.now();
  const diff = Math.max(0, endMs - now);
  if (diff === 0) return 'Завершена';
  const d = Math.floor(diff / (24 * 60 * 60 * 1000));
  const h = Math.floor((diff % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
  const m = Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000));
  const s = Math.floor((diff % (60 * 1000)) / 1000);
  if (d > 0) {
    return `${d} д. ${h} ч. ${m} мин.`;
  }
  return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/**
 * Оставшееся время до end_date (ISO).
 * Первый кадр — стабильный плейсхолдер «—», расчёт только в useEffect (нет рассинхрона SSR/гидратации из‑за Date.now()).
 */
export function usePromotionCountdown(endDate: string): string {
  const [left, setLeft] = useState('—');

  useEffect(() => {
    const endMs = new Date(endDate).getTime();
    if (Number.isNaN(endMs)) {
      setLeft('—');
      return;
    }
    const tick = () => setLeft(formatRemaining(endMs));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [endDate]);

  return left;
}
