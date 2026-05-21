'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { ErrorPageWithZinaBolaIllustration } from '@/components/errors/ErrorPageWithZinaBolaIllustration';

export default function NotFound() {
  return (
    <ErrorPageWithZinaBolaIllustration
      title="404 — Не найдено"
      description="Возможно, ссылка устарела. Давай вернёмся и найдём нужное."
    >
      <Button asChild>
        <Link href="/">На главную</Link>
      </Button>
      <Button asChild variant="secondary">
        <Link href="/catalog">В каталог</Link>
      </Button>
    </ErrorPageWithZinaBolaIllustration>
  );
}

