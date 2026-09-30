'use client';

import homePageLocales from '@/locales/home-page.json';
import { useUiMode } from '@/lib/providers/UiModeProvider';

export type HomePageHeroSideCategory = {
  label: string;
  slug: string;
  href: string;
  /** Опционально: URL картинки фона кнопки (например /categories/iphone.webp) */
  backgroundImage?: string;
};

export type HomePageQuickCatalogItem = {
  icon: string;
  label: string;
  href: string;
  /** Опционально: URL картинки фона кнопки (например /categories/iphone.webp) */
  backgroundImage?: string;
};

export type HomePageQuickCatalog = {
  bolaTitle: string;
  bolaSubtitle: string;
  zinaTitle: string;
  zinaSubtitle: string;
  bola: HomePageQuickCatalogItem[];
  zina: HomePageQuickCatalogItem[];
};

export type HomePageCopy = {
  promo: { sectionTitle: string; slideEyebrow: string };
  todayProducts: { title: string; subtitle: string; seeAll: string };
  installment: {
    title: string;
    lead: string;
    calculateCta: string;
    footnote: string;
    partnersLabel: string;
    calculatorHeader: string;
    collapse: string;
    priceLabel: string;
    priceAria: string;
    termLabel: string;
    monthlyLabel: string;
    disclaimer: string;
    checkoutCta: string;
    pickProductsCta: string;
    ringikBubble: string;
  };
  nearbyStores: {
    title: string;
    subtitle: string;
    detectLocation: string;
    allStores: string;
    route: string;
  };
  hero: { block1Note: string };
  heroSideCategoriesLeft?: HomePageHeroSideCategory[];
  heroSideCategoriesRight?: HomePageHeroSideCategory[];
  heroFullWidthCategory?: HomePageHeroSideCategory;
  quickCatalog?: HomePageQuickCatalog;
  heroDialogue?: {
    headlineLine1: string;
    headlineLine2: string;
    zinaBubble1: string;
    bolaBubble: string;
    zinaBubble2: string;
  };
};

function asCopy(mode: 'official' | 'svoi'): HomePageCopy {
  return (mode === 'svoi' ? homePageLocales.svoi : homePageLocales.official) as HomePageCopy;
}

/** Тексты блоков главной из locales/home-page.json (official | svoi). */
export function useHomePageCopy(): HomePageCopy {
  const { mode } = useUiMode();
  return asCopy(mode === 'svoi' ? 'svoi' : 'official');
}
