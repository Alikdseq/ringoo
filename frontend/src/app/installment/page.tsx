'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { CURRENCY_SYMBOL } from '@/lib/constants';

const TERMS = [3, 6, 12, 24] as const;

export default function InstallmentPage() {
  const [price, setPrice] = useState<string>('50000');
  const [term, setTerm] = useState<(typeof TERMS)[number]>(12);

  const parsedPrice = Number(price);
  const monthly = useMemo(() => {
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return null;
    return parsedPrice / term;
  }, [parsedPrice, term]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-brand)] hover:underline"
        >
          <ChevronLeft className="h-4 w-4" />
          Назад на главную
        </Link>

        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          Рассрочка 0%
        </h1>
        <p className="mt-2 text-foreground-muted">
          Быстрый расчёт ежемесячного платежа. Итоговые условия подтверждает банк-партнёр.
        </p>

        <Card className="mt-6 space-y-5 rounded-[28px]">
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
                  className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                    term === t
                      ? 'border-[--color-brand] bg-[--color-brand-soft] text-[--color-brand]'
                      : 'border-border bg-white text-foreground hover:bg-zinc-50'
                  }`}
                >
                  {t} мес
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-zinc-50 p-5">
            <p className="text-sm text-foreground-muted">Ежемесячный платёж</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
              {monthly == null ? '—' : `${Math.round(monthly).toLocaleString('ru-RU')} ${CURRENCY_SYMBOL}`}
            </p>
            <p className="mt-2 text-xs text-foreground-muted">
              Расчёт примерный и не является офертой. Одобрение и условия зависят от банка.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button asChild fullWidth>
              <Link href="/checkout">Перейти к оформлению</Link>
            </Button>
            <Button asChild variant="secondary" fullWidth>
              <Link href="/catalog">Выбрать товары</Link>
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

