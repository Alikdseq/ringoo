'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { cn } from '@/lib/theme/utils';

const TERMS = [3, 6, 12, 24] as const;

interface InstallmentCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function InstallmentCalculatorModal({ isOpen, onClose }: InstallmentCalculatorModalProps) {
  const [price, setPrice] = useState<string>('50000');
  const [term, setTerm] = useState<(typeof TERMS)[number]>(12);

  const parsedPrice = Number(price);
  const monthly = useMemo(() => {
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return null;
    return parsedPrice / term;
  }, [parsedPrice, term]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={onClose}
          aria-label="Калькулятор рассрочки"
        >
          <motion.div
            className="mx-auto w-full max-w-3xl px-4 pt-6 sm:pt-10"
            initial={{ y: -24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -24, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 420, damping: 34 }}
            onClick={e => e.stopPropagation()}
          >
            <Card className="relative overflow-hidden rounded-[32px] p-6 sm:p-8">
              <button
                type="button"
                onClick={onClose}
                className={cn(
                  'absolute right-4 top-4 inline-flex h-11 w-11 items-center justify-center rounded-full',
                  'border border-border bg-white/90 shadow-sm backdrop-blur transition-colors hover:bg-white'
                )}
                aria-label="Закрыть"
              >
                <X className="h-5 w-5 text-foreground" />
              </button>

              <h3 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Рассрочка 0%
              </h3>
              <p className="mt-2 text-foreground-muted">
                Быстрый расчёт ежемесячного платежа. Итоговые условия подтверждает банк‑партнёр.
              </p>

              <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
                <div className="space-y-5">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Стоимость покупки</label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        inputMode="numeric"
                        min={0}
                        value={price}
                        onChange={e => setPrice(e.target.value)}
                        className="w-full"
                        aria-label="Стоимость покупки"
                      />
                      <span className="shrink-0 text-sm text-foreground-muted">{CURRENCY_SYMBOL}</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground">Срок</label>
                    <div className="flex flex-wrap gap-2">
                      {TERMS.map(t => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setTerm(t)}
                          className={cn(
                            'rounded-full border px-4 py-2 text-sm font-medium transition-colors',
                            term === t
                              ? 'border-[--color-brand] bg-[--color-brand-soft] text-[--color-brand]'
                              : 'border-border bg-white text-foreground hover:bg-zinc-50'
                          )}
                        >
                          {t} мес
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-zinc-50 p-6">
                  <p className="text-sm text-foreground-muted">Ежемесячный платёж</p>
                  <p className="mt-1 text-4xl font-semibold tracking-tight text-foreground">
                    {monthly == null
                      ? '—'
                      : `${Math.round(monthly).toLocaleString('ru-RU')} ${CURRENCY_SYMBOL}`}
                  </p>
                  <p className="mt-2 text-xs text-foreground-muted">
                    Расчёт примерный и не является офертой. Одобрение и условия зависят от банка.
                  </p>

                  <div className="mt-5 flex flex-col gap-2">
                    <Button asChild fullWidth>
                      <Link href="/checkout">Перейти к оформлению</Link>
                    </Button>
                    <Button asChild variant="secondary" fullWidth>
                      <Link href="/catalog">Выбрать товары</Link>
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

