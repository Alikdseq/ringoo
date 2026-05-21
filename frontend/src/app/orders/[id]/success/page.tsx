'use client';

import type { ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import type { Order } from '@/types';
import { getOrder } from '@/lib/api/services/orders.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { CURRENCY_SYMBOL } from '@/lib/constants';

interface PageProps {
  params: { id: string };
}

function OrderInfo({ order }: { order: Order }): ReactElement {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col items-center text-center">
        <CheckCircle2 className="mb-3 h-12 w-12 text-brand" />
        <h1 className="mb-1 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          Заказ оформлен
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Спасибо за заказ! Ниже — краткая информация по нему.
        </p>
      </div>

      <Card className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <div>
            <p className="text-zinc-500 dark:text-zinc-400">Номер заказа</p>
            <p className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {order.order_number}
            </p>
          </div>
          <div>
            <p className="text-zinc-500 dark:text-zinc-400">Статус</p>
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{order.status}</p>
          </div>
          <div>
            <p className="text-zinc-500 dark:text-zinc-400">Сумма заказа</p>
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
              {order.total_amount} {CURRENCY_SYMBOL}
            </p>
          </div>
        </div>

        <div className="border-t border-dashed border-zinc-200 pt-3 text-sm dark:border-zinc-800">
          <p className="mb-1 font-medium text-zinc-900 dark:text-zinc-50">Получатель</p>
          <p className="text-zinc-600 dark:text-zinc-300">
            {order.full_name}, {order.phone}
            {order.email ? `, ${order.email}` : ''}
          </p>
        </div>

        <div className="border-t border-dashed border-zinc-200 pt-3 text-sm dark:border-zinc-800">
          <p className="mb-1 font-medium text-zinc-900 dark:text-zinc-50">Доставка и оплата</p>
          <p className="text-zinc-600 dark:text-zinc-300">
            Доставка: {order.delivery_type}. Оплата: {order.payment_type}.
          </p>
        </div>

        <div className="border-t border-dashed border-zinc-200 pt-3 text-sm dark:border-zinc-800">
          <p className="mb-1 font-medium text-zinc-900 dark:text-zinc-50">Товары</p>
          <ul className="space-y-1">
            {order.items.map(item => (
              <li key={item.id} className="flex items-center justify-between gap-2">
                <span className="text-zinc-700 dark:text-zinc-200">{item.product_title}</span>
                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                  {item.quantity} × {item.price} {CURRENCY_SYMBOL} = {item.item_total}{' '}
                  {CURRENCY_SYMBOL}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Card>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Button asChild variant="outline">
          <Link href="/order-status">Проверить заказ</Link>
        </Button>
        <Button asChild>
          <Link href="/catalog">Вернуться в каталог</Link>
        </Button>
      </div>
    </div>
  );
}

export default function OrderSuccessPage({ params }: PageProps): ReactElement {
  const { id } = params;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
        <p className="mb-3 text-sm text-red-600 dark:text-red-400">
          Не удалось загрузить данные заказа.
        </p>
        <Button asChild>
          <Link href="/catalog">Вернуться в каталог</Link>
        </Button>
      </div>
    );
  }

  return <OrderInfo order={data} />;
}
