'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { ChevronDown, MapPin, Phone, Truck } from 'lucide-react';
import { TYPOGRAPHY } from '@/lib/theme/typography';
import { cn } from '@/lib/theme/utils';

const StoresYandexMapDynamic = dynamic(
  () =>
    import('@/components/features/stores/StoresYandexMap').then(m => ({
      default: m.StoresYandexMap,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="h-72 w-full animate-pulse rounded-2xl bg-zinc-100 sm:h-80" />
    ),
  }
);

const ACCORDION_ITEMS = [
  {
    id: 'delivery',
    title: 'ДОСТАВКА',
    content:
      'Бесплатная доставка по Владикавказу и РСО-Алания от 100 ₽ — привезём домой или на работу. По России — курьером СДЭК. Заказы до 15:00 отправляем в тот же день.',
  },
  {
    id: 'payment',
    title: 'ОПЛАТА',
    content:
      'Наличными в магазине, банковской картой или по QR. Покупка в рассрочку/кредит оформляется через банк-партнёр. Расчёт платежа предварительный.',
  },
  {
    id: 'warranty',
    title: 'ГАРАНТИЯ',
    content:
      'Официальная гарантия на всю технику. Условия возврата и обмена — в соответствии с законом о защите прав потребителей.',
  },
];

export function DeliveryPaymentSection() {
  const [openId, setOpenId] = useState<string | null>(ACCORDION_ITEMS[0].id);

  return (
    <section
      id="delivery-payment"
      className="scroll-mt-20 border-t border-border bg-background px-4 py-12 sm:px-6 lg:px-8"
    >
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <h2 className={TYPOGRAPHY.h2 + ' mb-3 text-foreground'}>Доставка, оплата, гарантия</h2>

          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800">
            <Truck className="h-4 w-4" aria-hidden />
            Доставка бесплатно от 100 ₽ — домой или на работу
          </div>

          <div className="rounded-xl border border-border bg-white">
            {ACCORDION_ITEMS.map((item, i) => (
              <div key={item.id} className={cn('border-border', i > 0 && 'border-t')}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left transition-colors hover:bg-zinc-50"
                  onClick={() => setOpenId(prev => (prev === item.id ? null : item.id))}
                  aria-expanded={openId === item.id}
                >
                  <span
                    className={
                      TYPOGRAPHY.body + ' font-semibold uppercase tracking-wide text-foreground'
                    }
                  >
                    {item.title}
                  </span>
                  <ChevronDown
                    className={cn(
                      'h-5 w-5 shrink-0 text-foreground-muted transition-transform',
                      openId === item.id && 'rotate-180'
                    )}
                  />
                </button>
                {openId === item.id && (
                  <div className="border-t border-border bg-zinc-50/50 px-4 py-3">
                    <p className="text-sm leading-relaxed text-foreground-muted">{item.content}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="relative overflow-hidden rounded-xl border border-border bg-white">
          <StoresYandexMapDynamic heightClass="h-72 sm:h-[22rem] lg:h-[26rem]" className="rounded-none border-0" />
          <div className="border-t border-border p-4 text-sm text-foreground-muted">
            <p className="flex items-center gap-2 font-semibold text-foreground">
              <MapPin className="h-4 w-4 text-brand" aria-hidden /> Все магазины Ringoo на карте
            </p>
            <p className="mt-1 flex items-center gap-2">
              <Phone className="h-4 w-4 text-brand" aria-hidden />
              <a href="tel:+79184157788" className="hover:underline">+7 (918) 415-77-88</a>
              <span>· г. Владикавказ, ул. Весенняя 19Г</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
