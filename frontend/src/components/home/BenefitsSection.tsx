'use client';

import { BadgeCheck, ShieldCheck, Truck, Wrench } from 'lucide-react';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { benefitsHeading, benefitsItems, benefitsLead } from '@/lib/ui-mode/copy';
import { cn } from '@/lib/theme/utils';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS } from '@/lib/theme/spacing';

const ICON_BY_ID: Record<string, typeof ShieldCheck> = {
  delivery: Truck,
  warranty: ShieldCheck,
  official: BadgeCheck,
  service: Wrench,
};

export function BenefitsSection() {
  const { mode } = useUiMode();
  const items = benefitsItems(mode);

  return (
    <section className={HOME_SECTION_CLASS}>
      <div className={HOME_SECTION_INNER_CLASS}>
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
            {benefitsHeading(mode)}
          </h2>
          <p className="mt-2 text-base text-foreground-muted sm:text-lg">{benefitsLead(mode)}</p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4 lg:gap-7">
          {items.map(({ id, title, subtitle }) => {
            const Icon = ICON_BY_ID[id] ?? ShieldCheck;
            const isDelivery = id === 'delivery';
            return (
              <div
                key={id}
                className={cn(
                  'rounded-[32px] border px-6 py-6 transition-shadow sm:px-7 sm:py-7',
                  isDelivery
                    ? 'border-emerald-200 bg-emerald-50/60 hover:shadow-[0_10px_28px_rgba(16,185,129,0.18)]'
                    : 'border-border bg-white hover:shadow-md'
                )}
              >
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'flex h-12 w-12 items-center justify-center rounded-2xl',
                      isDelivery
                        ? 'bg-emerald-600/10 text-emerald-700'
                        : 'bg-[--color-brand-soft] text-[--color-brand]'
                    )}
                  >
                    <Icon className="h-6 w-6" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className={cn('text-base font-semibold', isDelivery ? 'text-emerald-900' : 'text-foreground')}>
                      {title}
                    </p>
                    <p className={cn('mt-1 text-sm', isDelivery ? 'text-emerald-800/85' : 'text-foreground-muted')}>
                      {subtitle}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

