'use client';

import Link from 'next/link';
import { Gift, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/theme/utils';
import { useRef } from 'react';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';

type GiftTile = {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  tone: 'mint' | 'sky' | 'zinc';
};

const TILES: GiftTile[] = [
  {
    id: 'parents',
    title: 'Для родителей',
    subtitle: 'Полезные гаджеты без лишних настроек.',
    href: '/catalog?category=samsung',
    tone: 'mint',
  },
  {
    id: 'kids',
    title: 'Для детей',
    subtitle: 'Наушники, аксессуары, игры — радость сразу.',
    href: '/catalog?category=iphone',
    tone: 'sky',
  },
  {
    id: 'for-him-her',
    title: 'Для неё / него',
    subtitle: 'Стильно. Практично. В подарок — идеально.',
    href: '/catalog?category=iphone',
    tone: 'zinc',
  },
];

const toneClass: Record<GiftTile['tone'], string> = {
  mint: 'bg-[radial-gradient(circle_at_20%_10%,rgba(34,197,94,0.18),transparent_55%),linear-gradient(180deg,#ffffff,#f6fff8)]',
  sky: 'bg-[radial-gradient(circle_at_20%_10%,rgba(59,130,246,0.16),transparent_55%),linear-gradient(180deg,#ffffff,#f6faff)]',
  zinc: 'bg-[radial-gradient(circle_at_20%_10%,rgba(24,24,27,0.10),transparent_55%),linear-gradient(180deg,#ffffff,#fafafa)]',
};

export function GiftTilesSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const ringik = useRingikIntersectionTrigger(sectionRef, 'home_gifts_gift');
  return (
    <section ref={sectionRef} className="relative bg-background px-2 py-12 sm:px-4 lg:px-4">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-foreground sm:text-3xl">Подарки</h2>
            <p className="mt-2 text-base text-foreground-muted sm:text-lg">Выбрал подарок?</p>
          </div>
          <Link href="/catalog" className="text-sm font-medium text-brand hover:underline sm:text-base">
            Смотреть всё
          </Link>
        </div>

        <div className="grid gap-5 lg:grid-cols-3 lg:gap-7">
          {TILES.map(tile => (
            <Link
              key={tile.id}
              href={tile.href}
              className={cn(
                'group relative overflow-hidden rounded-[32px] border border-border',
                'p-6 sm:p-8',
                'transition-shadow hover:shadow-md',
                toneClass[tile.tone]
              )}
            >
              <div className="absolute -right-8 -top-10 opacity-[0.12]" aria-hidden>
                <Gift className="h-40 w-40 text-foreground" />
              </div>

              <p className="text-lg font-semibold tracking-tight text-foreground sm:text-xl">
                {tile.title}
              </p>
              <p className="mt-2 max-w-sm text-sm text-foreground-muted">{tile.subtitle}</p>

              <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/70 px-4 py-2 text-sm font-medium text-foreground backdrop-blur transition-colors group-hover:bg-white">
                Смотреть <ArrowRight className="h-4 w-4" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      <Ringik
        pose="gift"
        placement="fixed-top-right"
        visible={ringik.visible}
        showMessage={ringik.showMessage}
        message="Для родителей? Для неё? Жми сюда!"
        className="top-1/2 -translate-y-1/2 translate-x-[38%] sm:translate-x-[35%]"
      />
    </section>
  );
}

