'use client';

import { useState } from 'react';
import type { ProductDetail } from '@/types';
import { stripDescriptionHtml } from '@/lib/format-description';
import { cn } from '@/lib/theme/utils';
import { FreeDeliveryHighlight } from '@/components/ui/FreeDeliveryBadge';

const TABS = [
  { id: 'description', label: 'Описание' },
  { id: 'warranty', label: 'Гарантия' },
  { id: 'delivery', label: 'Оплата и доставка' },
] as const;

interface ProductTabsProps {
  product: ProductDetail;
}

export function ProductTabs({ product }: ProductTabsProps) {
  const [active, setActive] = useState<(typeof TABS)[number]['id']>('description');

  return (
    <section className="mt-10 border-t border-border pt-6">
      <div className="border-b border-border">
        <nav className="flex gap-6" aria-label="Табы товара">
          {TABS.map(tab => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActive(tab.id)}
              className={cn(
                'border-b-2 pb-3 text-sm font-medium transition-colors',
                active === tab.id
                  ? 'border-zinc-900 text-foreground'
                  : 'border-transparent text-foreground-muted hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="mt-4 min-h-[120px]">
        {active === 'description' && (
          <div className="prose prose-sm max-w-none text-foreground">
            {product.description ? (
              <div className="whitespace-pre-wrap">{stripDescriptionHtml(product.description)}</div>
            ) : (
              <p className="text-foreground-muted">Описание товара пока не добавлено.</p>
            )}
            {product.specs && product.specs.length > 0 && (
              <>
                <h4 className="mt-4 font-semibold text-foreground">Характеристики</h4>
                <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                  {product.specs.map(spec => (
                    <div key={spec.name} className="flex gap-2">
                      <dt className="text-foreground-muted">{spec.name}:</dt>
                      <dd className="text-foreground">{spec.value}</dd>
                    </div>
                  ))}
                </dl>
              </>
            )}
          </div>
        )}
        {active === 'warranty' && (
          <p className="text-sm text-foreground-muted">
            Официальная гарантия на всю технику. Условия возврата и обмена — в соответствии с
            законом о защите прав потребителей. Подробности уточняйте у менеджера.
          </p>
        )}
        {active === 'delivery' && (
          <div className="space-y-3 text-sm text-foreground-muted">
            <FreeDeliveryHighlight />
            <p>
              По Владикавказу и РСО-Алания — бесплатная доставка от 100 ₽. Привезём домой или на
              работу — куда удобно. По России — курьером СДЭК.
            </p>
            <p>
              Оплата: наличными в магазине, картой, в рассрочку через банк-партнёр. Цена и наличие
              уточняются менеджером после заявки.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
