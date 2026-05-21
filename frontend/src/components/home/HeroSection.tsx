'use client';

import Link from 'next/link';
import { useRef } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { TYPOGRAPHY } from '@/lib/theme/typography';

export function HeroSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  });

  const yBg = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const opacityBg = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const yContent = useTransform(scrollYProgress, [0, 0.4], [0, 80]);
  const opacityContent = useTransform(scrollYProgress, [0, 0.35], [1, 0]);

  return (
    <section
      ref={ref}
      className="relative flex min-h-[90vh] flex-col items-center justify-center overflow-hidden bg-background px-4 py-20"
    >
      {/* Parallax — градиент (3D модель временно отключена) */}
      <motion.div
        className="absolute inset-0 flex items-center justify-center"
        style={{ y: yBg, opacity: opacityBg }}
        aria-hidden
      >
        <>
          <div className="h-[140%] w-[140%] rounded-full bg-gradient-to-br from-brand-soft/40 via-brand/10 to-transparent blur-3xl" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_0%,var(--color-brand-soft)/20%,transparent)]" />
        </>
      </motion.div>

      {/* Заголовок и кнопка */}
      <motion.div
        className="relative z-10 flex max-w-2xl flex-col items-center text-center"
        style={{ y: yContent, opacity: opacityContent }}
      >
        <motion.h1
          className={TYPOGRAPHY.h1 + ' mb-4 text-foreground'}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          Электроника с доставкой
        </motion.h1>
        <motion.p
          className={TYPOGRAPHY.body + ' mb-8 text-foreground-muted'}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          Каталог товаров и акции — всё в одном месте
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
        >
          <Link
            href="/catalog"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-brand px-8 text-base font-medium text-white transition-colors hover:bg-[var(--color-brand-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
          >
            В каталог
            <ArrowRight className="h-4 w-4" />
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}
