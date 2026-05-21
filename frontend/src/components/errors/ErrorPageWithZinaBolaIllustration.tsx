'use client';

import Image from 'next/image';
import type { ReactNode } from 'react';

const ILLUSTRATION = '/ZINA%20BOLA/404.png';

/** Общая вёрстка для error / 404 с иллюстрацией из public (без смены глобальной темы). */
export function ErrorPageWithZinaBolaIllustration({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="relative flex min-h-[70vh] flex-col items-center justify-center px-4 py-10 text-center sm:px-6 lg:px-8">
      <div className="relative mx-auto mb-6 h-48 w-full max-w-lg sm:h-56 md:h-64">
        <Image
          src={ILLUSTRATION}
          alt="Зина и Бола"
          fill
          className="object-contain"
          priority
          sizes="(max-width: 768px) 100vw, 512px"
        />
      </div>
      <h1 className="text-2xl font-semibold text-foreground">{title}</h1>
      <p className="mt-2 max-w-md text-sm text-foreground-muted">{description}</p>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">{children}</div>
    </div>
  );
}
