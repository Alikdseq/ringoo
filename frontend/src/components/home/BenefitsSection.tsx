'use client';

import { BadgeCheck, ShieldCheck, Wrench } from 'lucide-react';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { benefitsHeading, benefitsItems, benefitsLead } from '@/lib/ui-mode/copy';
import { cn } from '@/lib/theme/utils';

const ICON_BY_ID: Record<string, typeof ShieldCheck> = {
  warranty: ShieldCheck,
  official: BadgeCheck,
  service: Wrench,
};

export function BenefitsSection() {
  const { mode } = useUiMode();
  const items = benefitsItems(mode);

  return (
    <section className="bg-background px-2 py-12 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">
            {benefitsHeading(mode)}
          </h2>
          <p className="mt-2 text-base text-foreground-muted sm:text-lg">{benefitsLead(mode)}</p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 lg:gap-7">
          {items.map(({ id, title, subtitle }) => {
            const Icon = ICON_BY_ID[id] ?? ShieldCheck;
            return (
              <div
                key={id}
                className={cn(
                  'rounded-[32px] border border-border bg-white px-6 py-6 sm:px-7 sm:py-7',
                  'transition-shadow hover:shadow-md'
                )}
              >
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[--color-brand-soft] text-[--color-brand]">
                    <Icon className="h-6 w-6" aria-hidden />
                  </div>
                  <div className="min-w-0">
                    <p className="text-base font-semibold text-foreground">{title}</p>
                    <p className="mt-1 text-sm text-foreground-muted">{subtitle}</p>
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

