'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ScrollRevealSection } from './ScrollRevealSection';
import { TYPOGRAPHY, TYPOGRAPHY_MUTED } from '@/lib/theme/typography';

export function HomeCta() {
  return (
    <section className="border-t border-border bg-background px-4 py-20 sm:px-6 lg:px-8">
      <ScrollRevealSection className="mx-auto max-w-xl text-center">
        <h2 className={TYPOGRAPHY.h2 + ' text-foreground'}>Готовы выбрать технику?</h2>
        <p className={TYPOGRAPHY_MUTED.bodySmall + ' mt-3'}>
          Перейдите в каталог и найдите нужный товар
        </p>
        <motion.div
          className="mt-6"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <Link
            href="/catalog"
            className="inline-flex h-11 items-center justify-center rounded-full bg-brand px-8 text-base font-medium text-white transition-colors hover:bg-[var(--color-brand-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
          >
            Открыть каталог
          </Link>
        </motion.div>
      </ScrollRevealSection>
    </section>
  );
}
