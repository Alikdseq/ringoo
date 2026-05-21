'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { TYPOGRAPHY } from '@/lib/theme/typography';
import { cn } from '@/lib/theme/utils';

const ACCORDION_ITEMS = [
  {
    id: 'delivery',
    title: 'ДОСТАВКА',
    content:
      'Доставка по России курьером СДЭК. По Владикавказу и РСО-Алания — курьером или самовывоз. Заказы до 15:00 отправляем в тот же день. Стоимость и срок рассчитываются при оформлении заказа.',
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
        {/* Аккордеон */}
        <div>
          <h2 className={TYPOGRAPHY.h2 + ' mb-6 text-foreground'}>Доставка, оплата, гарантия</h2>
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

        {/* Карта + блок контактов */}
        <div className="relative overflow-hidden rounded-xl border border-border bg-zinc-100">
          <div className="aspect-[4/3] w-full bg-zinc-200">
            {/* Заглушка карты — позже подставить Яндекс.Карты */}
            <div className="flex h-full items-center justify-center text-sm text-foreground-muted">
              Карта (Яндекс.Карты)
            </div>
          </div>
          <div className="absolute bottom-4 left-4 right-4 rounded-lg border border-border bg-white/95 p-4 shadow-lg backdrop-blur sm:right-auto sm:w-72">
            <h3 className="mb-2 font-semibold text-foreground">Адрес и контакты</h3>
            <p className="text-sm text-foreground-muted">+7 (918) 415-77-88</p>
            <p className="mt-1 text-sm text-foreground-muted">Г. Владикавказ, ул. Весенняя 19Г</p>
            <a
              href="https://yandex.ru/maps"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-sm text-brand hover:underline"
            >
              Как добраться
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
