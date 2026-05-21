'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { ErrorPageWithZinaBolaIllustration } from '@/components/errors/ErrorPageWithZinaBolaIllustration';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    void error;
  }, [error]);

  return (
    <ErrorPageWithZinaBolaIllustration
      title="Ошибка"
      description="Мы уже разбираемся. Попробуй обновить или вернуться в каталог."
    >
      <Button type="button" onClick={reset}>
        Попробовать снова
      </Button>
      <Button asChild variant="secondary">
        <Link href="/catalog">В каталог</Link>
      </Button>
    </ErrorPageWithZinaBolaIllustration>
  );
}

