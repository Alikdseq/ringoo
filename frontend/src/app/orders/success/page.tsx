'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

function OrderSuccessContent() {
  const searchParams = useSearchParams();
  const orderNumber = searchParams.get('order_number') ?? '';

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col items-center text-center">
        <CheckCircle2 className="mb-3 h-12 w-12 text-brand" />
        <h1 className="mb-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Заказ оформлен
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Спасибо за заказ! Подробности и статус мы отправим по SMS и email.
        </p>
      </div>

      {orderNumber && (
        <Card className="mb-6 space-y-2">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Номер заказа</p>
          <p className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">{orderNumber}</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Сохраните номер — по нему можно проверить статус заказа.
          </p>
        </Card>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Button asChild variant="outline">
          <Link href="/order-status">Проверить статус заказа</Link>
        </Button>
        <Button asChild>
          <Link href="/catalog">Вернуться в каталог</Link>
        </Button>
      </div>
    </div>
  );
}

export default function OrderSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="h-12 w-12 animate-pulse rounded-full bg-zinc-200 mx-auto mb-3" />
          <div className="h-8 w-64 animate-pulse rounded bg-zinc-100 mx-auto" />
        </div>
      }
    >
      <OrderSuccessContent />
    </Suspense>
  );
}
