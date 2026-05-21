'use client';

import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, ChevronDown } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/theme/utils';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';

const PARTNERS = [
  { id: 'partner-1', label: 'Тинькофф' },
  { id: 'partner-2', label: 'Альфа' },
  { id: 'partner-3', label: 'Сбер' },
];

const TERMS = [3, 6, 12, 24] as const;

export function InstallmentZeroSection() {
  const home = useHomePageCopy();
  const i = home.installment;
  const sectionRef = useRef<HTMLElement>(null);
  const ringik = useRingikIntersectionTrigger(sectionRef, 'home_installment_pointing_v2', {
    bubbleMs: 4000,
    visibleMs: 6000,
    threshold: 0.35,
  });
  const [calculatorOpen, setCalculatorOpen] = useState(false);
  const [price, setPrice] = useState<string>('50000');
  const [term, setTerm] = useState<(typeof TERMS)[number]>(12);

  const parsedPrice = Number(price);
  const monthly = useMemo(() => {
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) return null;
    return parsedPrice / term;
  }, [parsedPrice, term]);

  return (
    <section ref={sectionRef} className="relative bg-background px-2 py-12 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          className={cn(
            'relative overflow-hidden rounded-[32px] border border-border bg-white',
            'px-5 py-12 sm:px-10 sm:py-14 lg:min-h-[420px] lg:px-14'
          )}
        >
          <div
            className={cn(
              'pointer-events-none absolute -right-8 -top-14 select-none',
              'text-[200px] font-semibold leading-none tracking-tight',
              'text-zinc-900/[0.06] sm:text-[260px] lg:text-[320px]'
            )}
            aria-hidden
          >
            0%
          </div>

          <div className="relative grid gap-10 lg:grid-cols-[1.25fr_0.75fr] lg:items-center">
            <div>
              <h2 className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                {i.title}
              </h2>
              <p className="mt-3 max-w-2xl text-base text-foreground-muted sm:text-lg">{i.lead}</p>

              <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
                <div className="relative w-full sm:w-auto">
                  <Button
                    type="button"
                    className="w-full sm:w-auto"
                    onClick={() => setCalculatorOpen(v => !v)}
                  >
                    {i.calculateCta} <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
                <p className="text-sm text-foreground-muted">{i.footnote}</p>
              </div>
            </div>

            <div className="relative flex flex-col items-start gap-3">
              <p className="text-sm font-medium text-foreground">{i.partnersLabel}</p>
              <div className="flex flex-wrap gap-2">
                {PARTNERS.map(p => (
                  <span
                    key={p.id}
                    className={cn(
                      'inline-flex items-center rounded-full border border-border bg-zinc-50 px-4 py-2',
                      'text-sm font-medium text-foreground',
                      'transition-colors hover:bg-zinc-100'
                    )}
                  >
                    {p.label}
                  </span>
                ))}
              </div>

              {/* Мобайл: Рингик над "Банки-партнёры", правее текста */}
              <Ringik
                pose="pointing"
                placement="absolute"
                visible={ringik.visible}
                showMessage={ringik.showMessage}
                message={i.ringikBubble}
                bubblePlacement="left"
                className="right-60 top-[20px] -translate-y-full scale-[1.2] sm:hidden"
              />
            </div>
          </div>

          {/* Рингик внизу слева внутimage.pngри карточки (как на макете) */}
          <Ringik
            pose="pointing"
            placement="absolute"
            visible={ringik.visible}
            showMessage={ringik.showMessage}
            message={i.ringikBubble}
            bubblePlacement="left"
            className="hidden sm:block left-6 top-[72%] scale-[1.5] sm:left-8 sm:top-[70%] lg:top-[68%]"
          />

          <AnimatePresence initial={false}>
            {calculatorOpen && (
              <motion.div
                key="installment-calculator"
                initial={{ height: 0, opacity: 0, y: -6 }}
                animate={{ height: 'auto', opacity: 1, y: 0 }}
                exit={{ height: 0, opacity: 0, y: -6 }}
                transition={{ type: 'spring', stiffness: 420, damping: 38 }}
                className="relative mt-10 overflow-hidden"
              >
                <div className="mb-6 flex items-center justify-between gap-4 border-t border-border pt-6">
                  <p className="text-sm font-medium text-foreground">{i.calculatorHeader}</p>
                  <button
                    type="button"
                    onClick={() => setCalculatorOpen(false)}
                    className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-zinc-50"
                  >
                    {i.collapse} <ChevronDown className="h-4 w-4 rotate-180" />
                  </button>
                </div>

                <Card className="rounded-[28px] border border-border bg-zinc-50/60 p-6 sm:p-8">
                  <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
                    <div className="space-y-6">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">{i.priceLabel}</label>
                        <div className="flex items-center gap-3">
                          <Input
                            type="number"
                            inputMode="numeric"
                            min={0}
                            value={price}
                            onChange={e => setPrice(e.target.value)}
                            className="w-full bg-white"
                            aria-label={i.priceAria}
                          />
                          <span className="shrink-0 text-sm text-foreground-muted">
                            {CURRENCY_SYMBOL}
                          </span>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">{i.termLabel}</label>
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

                    <div className="rounded-2xl border border-border bg-white p-6">
                      <p className="text-sm text-foreground-muted">{i.monthlyLabel}</p>
                      <p className="mt-1 text-4xl font-semibold tracking-tight text-foreground">
                        {monthly == null
                          ? '—'
                          : `${Math.round(monthly).toLocaleString('ru-RU')} ${CURRENCY_SYMBOL}`}
                      </p>
                      <p className="mt-2 text-xs text-foreground-muted">{i.disclaimer}</p>

                      <div className="mt-5 flex flex-col gap-2">
                        <Button asChild fullWidth>
                          <Link href="/checkout">{i.checkoutCta}</Link>
                        </Button>
                        <Button asChild variant="secondary" fullWidth>
                          <Link href="/catalog">{i.pickProductsCta}</Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

    </section>
  );
}

