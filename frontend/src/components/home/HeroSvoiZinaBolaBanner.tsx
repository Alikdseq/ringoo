'use client';

import type { ReactNode } from 'react';
import Image from 'next/image';
import { Comfortaa } from 'next/font/google';
import { useHomePageCopy } from '@/lib/locales/useHomePageCopy';
import { cn } from '@/lib/theme/utils';

const comfortaa = Comfortaa({
  weight: ['600', '700'],
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
});

const BOLA = '/ZINA%20BOLA/bola1.png';
const ZINA = '/ZINA%20BOLA/zina1.jpg';

const BUBBLE_BORDER = '#5fd92a';
const BUBBLE_BG = '#ebebeb';

function BubbleTail({ toward }: { toward: 'left' | 'right' | 'down' }) {
  if (toward === 'left') {
    return (
      <svg
        className="pointer-events-none absolute -left-[14px] top-[42%] z-[1] h-10 w-4 -translate-y-1/2 overflow-visible"
        viewBox="0 0 16 40"
        aria-hidden
      >
        <path
          d="M16 8 L16 32 L2 20 Z"
          fill={BUBBLE_BG}
          stroke={BUBBLE_BORDER}
          strokeWidth={2}
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  if (toward === 'right') {
    return (
      <svg
        className="pointer-events-none absolute -right-[14px] top-[38%] z-[1] h-10 w-4 -translate-y-1/2 overflow-visible"
        viewBox="0 0 16 40"
        aria-hidden
      >
        <path
          d="M0 8 L0 32 L14 20 Z"
          fill={BUBBLE_BG}
          stroke={BUBBLE_BORDER}
          strokeWidth={2}
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  return (
    <svg
      className="pointer-events-none absolute bottom-[-12px] left-[22%] z-[1] h-5 w-10 overflow-visible"
      viewBox="0 0 40 16"
      aria-hidden
    >
      <path
        d="M8 0 L32 0 L20 14 Z"
        fill={BUBBLE_BG}
        stroke={BUBBLE_BORDER}
        strokeWidth={2}
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SpeechBubble({
  children,
  className,
  tail,
}: {
  children: ReactNode;
  className?: string;
  tail: 'left' | 'right' | 'down';
}) {
  return (
    <div className={cn('relative z-10 drop-shadow-md', className)}>
      <div
        className="relative z-10 px-3.5 py-2.5 text-left text-[13px] font-semibold leading-snug text-neutral-900 sm:text-sm md:text-[15px]"
        style={{
          backgroundColor: BUBBLE_BG,
          border: `2px solid ${BUBBLE_BORDER}`,
          borderRadius: '55% 45% 48% 52% / 52% 48% 51% 49%',
        }}
      >
        {children}
      </div>
      <BubbleTail toward={tail === 'left' ? 'left' : tail === 'right' ? 'right' : 'down'} />
    </div>
  );
}

/**
 * Первый блок свойского режима: Бола слева, Зина справа, заголовок и пузыри по макету.
 * Comfortaa только в этом блоке.
 */
export function HeroSvoiZinaBolaBanner() {
  const copy = useHomePageCopy();
  const d = copy.heroDialogue;

  const line1 = d?.headlineLine1 ?? 'Техника без понтов,';
  const line2 = d?.headlineLine2 ?? 'но со статусом.';
  const zina1 = d?.zinaBubble1 ?? 'Бола, это точно ко мне';
  const bola = d?.bolaBubble ?? 'О, ед.\nЗа телефоном они';
  const zina2 = d?.zinaBubble2 ?? 'Ты и мне ничего не подарил';

  return (
    <section className="border-b border-border bg-white" aria-label="Свойский режим">
      <div className={cn('mx-auto max-w-7xl px-3 py-5 sm:px-6 sm:py-7', comfortaa.className)}>
        <div className="relative mx-auto min-h-[300px] sm:min-h-[340px] md:min-h-[400px] lg:min-h-[440px]">
          <h1 className="relative z-20 max-w-[min(100%,22rem)] text-left text-xl font-bold leading-tight tracking-tight text-black sm:max-w-md sm:text-2xl md:text-3xl lg:text-[2rem] lg:leading-tight">
            <span className="block">{line1}</span>
            <span className="block">{line2}</span>
          </h1>

          <SpeechBubble
            tail="right"
            className="absolute right-[4%] top-[6%] w-[min(46%,220px)] sm:right-[8%] sm:top-[8%] sm:w-[min(42%,260px)] md:right-[12%] md:w-[280px] lg:right-[14%]"
          >
            {zina1}
          </SpeechBubble>

          <SpeechBubble
            tail="left"
            className="absolute left-[22%] top-[34%] w-[min(52%,240px)] sm:left-[24%] sm:top-[36%] sm:w-[min(48%,280px)] md:left-[26%] md:w-[300px] lg:left-[28%]"
          >
            <span className="whitespace-pre-line">{bola}</span>
          </SpeechBubble>

          <SpeechBubble
            tail="down"
            className="absolute bottom-[18%] right-[2%] w-[min(50%,230px)] sm:bottom-[20%] sm:right-[4%] sm:w-[min(46%,270px)] md:bottom-[22%] md:right-[6%] md:w-[290px]"
          >
            {zina2}
          </SpeechBubble>

          <div className="pointer-events-none absolute bottom-0 left-[-2%] z-[5] h-[min(58vw,280px)] w-[min(46vw,240px)] sm:left-0 sm:h-[min(50vw,320px)] sm:w-[min(38vw,260px)] md:h-[360px] md:w-[280px] lg:h-[400px] lg:w-[300px]">
            <Image
              src={BOLA}
              alt=""
              fill
              className="object-contain object-bottom"
              sizes="(max-width: 768px) 46vw, 300px"
              priority
            />
          </div>

          <div className="pointer-events-none absolute bottom-0 right-[-2%] z-[5] h-[min(58vw,300px)] w-[min(46vw,250px)] sm:right-0 sm:h-[min(52vw,340px)] sm:w-[min(40vw,280px)] md:h-[380px] md:w-[300px] lg:h-[420px] lg:w-[320px]">
            <Image
              src={ZINA}
              alt=""
              fill
              className="object-contain object-bottom"
              sizes="(max-width: 768px) 46vw, 320px"
              priority
            />
          </div>
        </div>
      </div>
    </section>
  );
}
