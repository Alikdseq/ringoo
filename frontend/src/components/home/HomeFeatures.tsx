'use client';

import { Truck, Shield, Package } from 'lucide-react';
import { ScrollRevealSection } from './ScrollRevealSection';
import { TYPOGRAPHY, TYPOGRAPHY_MUTED } from '@/lib/theme/typography';

const features = [
  {
    icon: Truck,
    title: 'Доставка бесплатно от 100 ₽',
    description: 'Привезём домой или на работу — куда удобно',
  },
  { icon: Shield, title: 'Гарантия', description: 'Официальная гарантия на всю технику' },
  { icon: Package, title: 'Ассортимент', description: 'Электроника и аксессуары в одном каталоге' },
];

export function HomeFeatures() {
  return (
    <section className="border-t border-border bg-background px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <ScrollRevealSection className="mb-10 text-center">
          <h2 className={TYPOGRAPHY.h2 + ' text-foreground'}>Почему Ringoo</h2>
          <p className={TYPOGRAPHY_MUTED.bodySmall + ' mt-2'}>
            Удобно покупать и выгодно возвращаться
          </p>
        </ScrollRevealSection>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((item, i) => (
            <ScrollRevealSection
              key={item.title}
              className="rounded-xl border border-border bg-white p-6 shadow-sm transition-all duration-150 hover:shadow-md hover:-translate-y-0.5"
              transition={{
                duration: 0.45,
                delay: i * 0.08,
                ease: [0.25, 0.46, 0.45, 0.94] as const,
              }}
            >
              <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-brand">
                <item.icon className="h-5 w-5" />
              </div>
              <h3 className={TYPOGRAPHY.h3 + ' text-foreground'}>{item.title}</h3>
              <p className={TYPOGRAPHY_MUTED.bodySmall + ' mt-1'}>{item.description}</p>
            </ScrollRevealSection>
          ))}
        </div>
      </div>
    </section>
  );
}
