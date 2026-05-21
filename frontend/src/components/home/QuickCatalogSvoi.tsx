'use client';

import Image from 'next/image';
import Link from 'next/link';
import type { HomePageQuickCatalog, HomePageQuickCatalogItem } from '@/lib/locales/useHomePageCopy';
import { CATEGORY_HERO_IMAGE_BY_SLUG } from '@/components/home/categoryHeroImages';
import { cn } from '@/lib/theme/utils';

function categorySlugFromQuickHref(href: string): string | undefined {
  const q = href.indexOf('?');
  if (q === -1) return undefined;
  try {
    const c = new URLSearchParams(href.slice(q + 1)).get('category');
    return c || undefined;
  } catch {
    return undefined;
  }
}

/** Как `CategoryCard` в официальном херо: фото категории или градиент, оверлей, белый текст по центру. Тексты ссылок — из локалей. */
function SvoiLinkButton({ item }: { item: HomePageQuickCatalogItem }) {
  const slug = categorySlugFromQuickHref(item.href);
  const fromSlug = slug ? CATEGORY_HERO_IMAGE_BY_SLUG[slug] : undefined;
  const imageSrc = item.backgroundImage?.trim() || fromSlug;

  return (
    <Link
      href={item.href}
      className="group block w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2"
      aria-label={`Перейти: ${item.label}`}
    >
      <div
        className={cn(
          'relative w-full overflow-hidden rounded-2xl shadow-md ring-1 ring-black/5 transition-[transform,box-shadow] duration-300 will-change-transform',
          'hover:scale-[1.01] hover:shadow-lg sm:rounded-3xl',
          'min-h-[5rem] sm:min-h-[5.75rem]'
        )}
      >
        {imageSrc ? (
          <Image
            src={imageSrc}
            alt=""
            fill
            sizes="(max-width: 1024px) 50vw, 20vw"
            className="object-cover transition-[transform,filter] duration-500 ease-out group-hover:scale-105 group-hover:brightness-105"
            priority={false}
          />
        ) : (
          <div
            className="absolute inset-0 bg-gradient-to-br from-zinc-500 via-zinc-600 to-zinc-800"
            aria-hidden
          />
        )}
        <div
          className="absolute inset-0 bg-gradient-to-b from-black/45 via-black/30 to-black/50 sm:bg-gradient-to-r sm:from-black/60 sm:via-black/30 sm:to-black/20"
          aria-hidden
        />
        <span
          className={cn(
            'absolute inset-0 flex items-center justify-center px-2 text-center text-[10px] font-bold leading-tight tracking-tight text-white',
            'drop-shadow-[0_1px_3px_rgba(0,0,0,0.55)]',
            'sm:text-xs lg:text-sm xl:text-base'
          )}
        >
          {item.label}
        </span>
      </div>
    </Link>
  );
}

function Column({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: HomePageQuickCatalogItem[];
}) {
  return (
      <div className="flex min-h-0 w-full flex-col gap-3">
        <div className="mb-1">
          <h3 className="text-sm font-bold leading-tight text-foreground sm:text-base">{title}</h3>
          <p className="mt-0.5 text-xs font-medium text-foreground-muted sm:text-sm">{subtitle}</p>
        </div>
        <div className="flex w-full flex-col gap-3">
        {items.map((item, i) => (
          <SvoiLinkButton key={`${item.href}-${i}`} item={item} />
        ))}
      </div>
    </div>
  );
}

/** Мобилка: две колонки Бола | Зина подряд до 3D. */
export function QuickCatalogSvoiMobile({ data }: { data: HomePageQuickCatalog }) {
  return (
    <div className="order-1 lg:hidden">
      <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
        <Column title={data.bolaTitle} subtitle={data.bolaSubtitle} items={data.bola} />
        <Column title={data.zinaTitle} subtitle={data.zinaSubtitle} items={data.zina} />
      </div>
    </div>
  );
}

/** Десктоп: левая колонка сетки — от Болы. */
export function QuickCatalogSvoiDesktopBola({ data }: { data: HomePageQuickCatalog }) {
  return (
    <div className="hidden flex-col justify-center lg:flex">
      <Column title={data.bolaTitle} subtitle={data.bolaSubtitle} items={data.bola} />
    </div>
  );
}

/** Десктоп: правая колонка сетки — от Зины. */
export function QuickCatalogSvoiDesktopZina({ data }: { data: HomePageQuickCatalog }) {
  return (
    <div className="hidden flex-col justify-center lg:flex">
      <Column title={data.zinaTitle} subtitle={data.zinaSubtitle} items={data.zina} />
    </div>
  );
}
