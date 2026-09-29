'use client';

import Link from 'next/link';
import { LINK_PREFETCH_DEFAULT } from '@/lib/navigation/link-prefetch';
import Image from 'next/image';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { HomePageHeroSideCategory } from '@/lib/locales/useHomePageCopy';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { TYPOGRAPHY } from '@/lib/theme/typography';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';
import { heroCtaLabel, heroSubtitle, heroTitle } from '@/lib/ui-mode/copy';
import {
  QuickCatalogSvoiDesktopBola,
  QuickCatalogSvoiDesktopZina,
  QuickCatalogSvoiMobile,
} from '@/components/home/QuickCatalogSvoi';
import {
  QuickCatalogOfficialDesktopStack,
  QuickCatalogOfficialFullWidth,
  QuickCatalogOfficialMobile,
} from '@/components/home/QuickCatalogOfficial';
import { BLUR_DATA_URL } from '@/lib/performance/blur-placeholders';

export function HeroWithCategories() {
  const { mode } = useUiMode();
  const homeCopy = useHomePageCopy();
  const quickCatalog = homeCopy.quickCatalog;
  const heroLeft = homeCopy.heroSideCategoriesLeft ?? [];
  const heroRight = homeCopy.heroSideCategoriesRight ?? [];
  const heroFull = homeCopy.heroFullWidthCategory;
  const ref = useRef<HTMLElement>(null);
  const ringik = useRingikIntersectionTrigger(ref, 'home_categories_peeking_v2', {
    bubbleMs: 1400,
    visibleMs: 2000,
    threshold: 0.35,
    rootMargin: '-10% 0px 0px 0px',
  });
  const [ctaHover, setCtaHover] = useState(false);
  const [ctaHoverOnce, setCtaHoverOnce] = useState(false);

  const showOfficialHero =
    mode !== 'svoi' && heroLeft.length > 0 && heroRight.length > 0 && heroFull;

  /** Мобилка: длинная кнопка iPhone сверху, Infinix — на месте iPhone в левой колонке */
  const officialMobileQuickCatalog = useMemo((): {
    left: HomePageHeroSideCategory[];
    fullWidth?: HomePageHeroSideCategory;
  } | null => {
    if (!showOfficialHero || !heroFull) return null;
    const iphone = heroLeft.find(c => c.slug === 'iphone');
    if (!iphone) {
      return { left: heroLeft, fullWidth: heroFull };
    }
    return {
      left: [heroFull, ...heroLeft.filter(c => c.slug !== 'iphone')],
      fullWidth: iphone,
    };
  }, [showOfficialHero, heroFull, heroLeft]);

  useEffect(() => {
    try {
      setCtaHoverOnce(Boolean(sessionStorage.getItem('ringik_home_cta_hiding')));
    } catch {
      setCtaHoverOnce(false);
    }
  }, []);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  });

  const yBg = useTransform(scrollYProgress, [0, 1], [0, 80]);
  const opacityBg = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const yContent = useTransform(scrollYProgress, [0, 0.35], [0, 50]);
  const opacityContent = useTransform(scrollYProgress, [0, 0.3], [1, 0]);

  return (
    <section
      ref={ref}
      className="relative min-h-0 overflow-hidden bg-background px-4 py-6 sm:min-h-[72vh] sm:px-4 sm:py-8 lg:min-h-[85vh] lg:px-6"
    >
      <div className="mx-auto flex h-full max-w-7xl flex-col gap-3 sm:min-h-[68vh] sm:gap-6 lg:min-h-[75vh]">
        <div className="grid h-full min-h-0 flex-1 grid-cols-1 gap-4 lg:min-h-[75vh] lg:grid-cols-[1fr_1.6fr_1fr] lg:gap-6">
          {mode === 'svoi' && quickCatalog ? (
            <>
              <QuickCatalogSvoiMobile data={quickCatalog} />
              <QuickCatalogSvoiDesktopBola data={quickCatalog} />
            </>
          ) : showOfficialHero ? (
            <>
              <QuickCatalogOfficialMobile
                left={officialMobileQuickCatalog?.left ?? heroLeft}
                right={heroRight}
                fullWidth={officialMobileQuickCatalog?.fullWidth ?? heroFull ?? undefined}
              />
              <QuickCatalogOfficialDesktopStack items={heroLeft} />
            </>
          ) : null}

          <div className="relative order-2 min-h-[42vh] overflow-hidden rounded-3xl sm:min-h-[50vh] lg:order-none lg:min-h-[75vh]">
            {mode !== 'svoi' && (
              <div className="absolute inset-0" aria-hidden>
                <Image
                  src="/fon/fon.jpg"
                  alt=""
                  fill
                  className="object-cover object-center"
                  sizes="(max-width: 1024px) 100vw, 60vw"
                  quality={80}
                  priority
                  placeholder="blur"
                  blurDataURL={BLUR_DATA_URL}
                />
              </div>
            )}
            {mode === 'svoi' && (
              <motion.div
                className="absolute inset-0 flex items-center justify-center"
                style={{ y: yBg, opacity: opacityBg }}
                aria-hidden
              >
                <div className="h-[120%] w-[120%] rounded-full bg-gradient-to-br from-brand-soft/40 via-brand/10 to-transparent blur-3xl" />
                <motion.div
                  className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_50%,var(--color-brand-soft)/15%,transparent)]"
                  aria-hidden
                />
              </motion.div>
            )}
            {mode === 'svoi' && (
              <motion.div
                className="relative z-10 flex max-w-md flex-col items-center text-center"
                style={{ y: yContent, opacity: opacityContent }}
              >
                <motion.h1 className={TYPOGRAPHY.h1 + ' mb-3 text-foreground'}>
                  {heroTitle(mode)}
                </motion.h1>
                <motion.p className={TYPOGRAPHY.body + ' mb-6 text-foreground-muted'}>
                  {heroSubtitle(mode)}
                </motion.p>
                <Link
                  href="/catalog"
                  prefetch={LINK_PREFETCH_DEFAULT}
                  className="relative inline-flex h-10 items-center justify-center gap-2 rounded-full bg-brand px-6 text-sm font-medium text-white transition-colors hover:bg-[var(--color-brand-muted)]"
                >
                  {heroCtaLabel(mode)}
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </motion.div>
            )}
          </div>

          {mode === 'svoi' && quickCatalog ? (
            <QuickCatalogSvoiDesktopZina data={quickCatalog} />
          ) : showOfficialHero ? (
            <QuickCatalogOfficialDesktopStack items={heroRight} />
          ) : null}
        </div>

        {showOfficialHero && heroFull ? (
          <div className="hidden lg:block">
            <QuickCatalogOfficialFullWidth item={heroFull} />
          </div>
        ) : null}

        {mode !== 'svoi' && (
          <div className="relative flex justify-center pb-2">
            <Link
              href="/catalog"
              prefetch={LINK_PREFETCH_DEFAULT}
              className="relative inline-flex h-14 items-center justify-center gap-3 rounded-full bg-brand px-10 text-lg font-semibold text-white shadow-lg transition-colors hover:bg-[var(--color-brand-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
              onMouseEnter={() => {
                if (ctaHoverOnce) return;
                setCtaHover(true);
                try {
                  sessionStorage.setItem('ringik_home_cta_hiding', '1');
                  setCtaHoverOnce(true);
                } catch {
                  /* ignore */
                }
              }}
              onMouseLeave={() => setCtaHover(false)}
            >
              {heroCtaLabel(mode)}
              <ArrowRight className="h-5 w-5" />
              <Ringik
                pose="hiding"
                placement="absolute"
                visible={ctaHover}
                showMessage={ctaHover}
                message="Псс... тут выгодно!"
                className="pointer-events-none -right-12 -top-12 hidden lg:block"
              />
            </Link>
          </div>
        )}
      </div>

      <Ringik
        pose="peeking"
        placement="fixed-top-right"
        visible={ringik.visible}
        showMessage={ringik.showMessage}
        message={
          mode === 'svoi'
            ? 'Ткни по картинке — быстро найдёшь, родной.'
            : 'Нажми на иконку — найдёшь быстро'
        }
        className="pointer-events-none top-1/2 -right-4 hidden -translate-y-1/2 scale-100 sm:block sm:-right-8 sm:scale-[1.25]"
      />
    </section>
  );
}
