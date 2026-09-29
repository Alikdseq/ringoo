'use client';

import Image from 'next/image';
import Link from 'next/link';
import { LINK_PREFETCH_DEFAULT } from '@/lib/navigation/link-prefetch';
import type { HomePageHeroSideCategory } from '@/lib/locales/useHomePageCopy';
import { cn } from '@/lib/theme/utils';
import {
  QUICK_CATALOG_FROST_CLASS,
  QUICK_CATALOG_GLOW_CLASS,
  QUICK_CATALOG_IMAGE_CLASS,
  QUICK_CATALOG_LABEL_CLASS,
  QUICK_CATALOG_LIGHT_OVERLAY_CLASS,
  QUICK_CATALOG_SCRIM_CLASS,
  QUICK_CATALOG_SHELL_CLASS,
  quickCatalogBackgroundForSlug,
} from '@/components/home/quickCatalogBackgrounds';

const SLUG_GRADIENTS: Record<string, string> = {
  iphone: 'bg-[linear-gradient(145deg,#0f172a_0%,#14532d_38%,#16a34a_72%,#22c55e_100%)]',
  huawei: 'bg-[linear-gradient(145deg,#1e1b4b_0%,#7c3aed_45%,#a855f7_100%)]',
  realme: 'bg-[linear-gradient(145deg,#0c4a6e_0%,#0284c7_50%,#38bdf8_100%)]',
  samsung: 'bg-[linear-gradient(145deg,#042f2e_0%,#0d9488_35%,#059669_65%,#34d399_100%)]',
  xiaomi: 'bg-[linear-gradient(145deg,#450a0a_0%,#dc2626_45%,#f97316_100%)]',
  tecno: 'bg-[linear-gradient(145deg,#134e4a_0%,#0f766e_50%,#2dd4bf_100%)]',
  infinix: 'bg-[linear-gradient(145deg,#312e81_0%,#4f46e5_40%,#818cf8_100%)]',
};

function gradientForSlug(slug: string): string {
  return SLUG_GRADIENTS[slug] ?? SLUG_GRADIENTS.samsung;
}

function OfficialHeroCategoryButton({
  item,
  compact,
  wide,
}: {
  item: HomePageHeroSideCategory;
  compact?: boolean;
  wide?: boolean;
}) {
  const bgSrc = quickCatalogBackgroundForSlug(item.slug);

  return (
    <Link
      href={item.href}
      prefetch={LINK_PREFETCH_DEFAULT}
      className="group block h-full w-full min-h-0 flex-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
      aria-label={`Перейти в категорию «${item.label}»`}
    >
      <div
        className={cn(
          QUICK_CATALOG_SHELL_CLASS,
          compact ? 'min-h-[4.5rem] sm:min-h-[5rem]' : wide ? 'min-h-[4.5rem] sm:min-h-[5.5rem]' : 'min-h-[8rem]'
        )}
      >
        {bgSrc ? (
          <>
            <Image
              src={bgSrc}
              alt=""
              fill
              sizes={
                wide
                  ? '(max-width: 1024px) 100vw, 33vw'
                  : compact
                    ? '(max-width: 1024px) 45vw, 18vw'
                    : '(max-width: 1024px) 45vw, 22vw'
              }
              className={QUICK_CATALOG_IMAGE_CLASS}
              priority={item.slug === 'iphone'}
            />
            <div className={QUICK_CATALOG_GLOW_CLASS} aria-hidden />
            <div className={QUICK_CATALOG_LIGHT_OVERLAY_CLASS} aria-hidden />
            <div className={QUICK_CATALOG_SCRIM_CLASS} aria-hidden />
            <div className={QUICK_CATALOG_FROST_CLASS} aria-hidden />
          </>
        ) : (
          <div className={cn('absolute inset-0', gradientForSlug(item.slug))} aria-hidden />
        )}

        <span
          className={cn(
            QUICK_CATALOG_LABEL_CLASS,
            wide ? 'text-xl sm:text-2xl lg:text-3xl' : compact ? 'text-base sm:text-lg' : 'text-xl sm:text-2xl'
          )}
        >
          {item.label}
        </span>
      </div>
    </Link>
  );
}

export function QuickCatalogOfficialMobile({
  left,
  right,
  fullWidth,
}: {
  left: HomePageHeroSideCategory[];
  right: HomePageHeroSideCategory[];
  /** Infinix и прочие — на мобилке над сеткой категорий, всё блоком над фото херо */
  fullWidth?: HomePageHeroSideCategory;
}) {
  return (
    <div className="order-1 flex flex-col gap-2 sm:gap-3 lg:hidden">
      {fullWidth ? <QuickCatalogOfficialFullWidth item={fullWidth} /> : null}
      <div className="grid grid-cols-2 gap-2 sm:gap-3">
        <div className="flex flex-col gap-2 sm:gap-3">
          {left.map(item => (
            <OfficialHeroCategoryButton key={item.slug} item={item} compact />
          ))}
        </div>
        <div className="flex flex-col gap-2 sm:gap-3">
          {right.map(item => (
            <OfficialHeroCategoryButton key={item.slug} item={item} compact />
          ))}
        </div>
      </div>
    </div>
  );
}

export function QuickCatalogOfficialDesktopStack({
  items,
}: {
  items: HomePageHeroSideCategory[];
}) {
  return (
    <div className="hidden h-full min-h-[68vh] flex-col justify-center gap-3 lg:flex lg:min-h-[75vh] lg:gap-4">
      {items.map(item => (
        <OfficialHeroCategoryButton key={item.slug} item={item} compact />
      ))}
    </div>
  );
}

export function QuickCatalogOfficialFullWidth({
  item,
}: {
  item: HomePageHeroSideCategory;
}) {
  return (
    <div className="w-full">
      <OfficialHeroCategoryButton item={item} wide />
    </div>
  );
}
