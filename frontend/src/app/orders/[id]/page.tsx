'use client';

import type { ReactElement } from 'react';
import { useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Package,
  Truck,
  CreditCard,
  User as UserIcon,
  MessageCircle,
  RotateCcw,
} from 'lucide-react';
import type { Order } from '@/types';
import { getOrder, reorderOrder } from '@/lib/api/services/orders.service';
import { useAuth } from '@/lib/hooks/useAuth';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { isOrderIdParam } from '@/lib/validation/route-params';

function formatDate(date: string): string {
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleString();
}

function OrderStatusBadge({ status }: { status: string }): ReactElement {
  return (
    <span className="inline-flex items-center rounded-full bg-brand-soft px-3 py-1 text-xs font-medium text-brand-muted">
      {status}
    </span>
  );
}

function OrderDetail({
  order,
  onReorder,
  isReordering,
}: {
  order: Order;
  onReorder?: () => void;
  isReordering?: boolean;
}): ReactElement {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            Заказ №{order.order_number}
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Оформлен {formatDate(order.created_at)}
          </p>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <Card>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            <Package className="h-4 w-4" />
            Сводка заказа
          </div>
          <dl className="space-y-1 text-sm text-zinc-600 dark:text-zinc-300">
            <div className="flex justify-between">
              <dt>Сумма товаров</dt>
              <dd>
                {order.total_amount} {CURRENCY_SYMBOL}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>Стоимость доставки</dt>
              <dd>
                {order.delivery_cost} {CURRENCY_SYMBOL}
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            <UserIcon className="h-4 w-4" />
            Получатель
          </div>
          <div className="space-y-1 text-sm text-zinc-600 dark:text-zinc-300">
            <p>{order.full_name}</p>
            <p>{order.phone}</p>
            {order.email && <p>{order.email}</p>}
            {order.comment && (
              <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
                Комментарий: {order.comment}
              </p>
            )}
          </div>
        </Card>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <Card>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            <Truck className="h-4 w-4" />
            Доставка
          </div>
          <div className="space-y-1 text-sm text-zinc-600 dark:text-zinc-300">
            <p>Тип доставки: {order.delivery_type}</p>
            {order.store && <p>Магазин: {order.store}</p>}
          </div>
        </Card>

        <Card>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            <CreditCard className="h-4 w-4" />
            Оплата
          </div>
          <div className="space-y-1 text-sm text-zinc-600 dark:text-zinc-300">
            <p>Способ оплаты: {order.payment_type}</p>
          </div>
        </Card>
      </div>

      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          Товары в заказе
        </h2>
        <ul className="divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
          {order.items.map(item => (
            <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div>
                <p className="font-medium text-zinc-900 dark:text-zinc-50">{item.product_title}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {item.quantity} × {item.price} {CURRENCY_SYMBOL}
                </p>
              </div>
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                {item.item_total} {CURRENCY_SYMBOL}
              </p>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {onReorder && (
            <Button
              variant="outline"
              className="flex items-center gap-2"
              onClick={onReorder}
              loading={isReordering}
              disabled={isReordering}
            >
              <RotateCcw className="h-4 w-4" />
              Повтор заказа
            </Button>
          )}
          <Button variant="outline" className="flex items-center gap-2">
            <MessageCircle className="h-4 w-4" />
            Связаться с поддержкой
          </Button>
        </div>
        <div className="flex gap-2 sm:justify-end">
          <Link
            href="/orders"
            className="inline-flex items-center justify-center rounded-full border border-zinc-300 px-5 py-2 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-100 dark:hover:bg-zinc-900"
          >
            К списку заказов
          </Link>
          <Link
            href="/catalog"
            className="inline-flex items-center justify-center rounded-full bg-[var(--color-brand)] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-brand-muted)]"
          >
            В каталог
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function OrderDetailPage(): ReactElement {
  const params = useParams<{ id: string }>();
  const rawId = params.id;
  const id = typeof rawId === 'string' ? rawId : '';
  const idValid = isOrderIdParam(id);
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, hasToken } = useAuth();

  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
    enabled: isAuthenticated && idValid,
  });

  const reorderMutation = useMutation({
    mutationFn: () => reorderOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      router.push('/cart');
    },
  });

  const handleReorder = () => {
    reorderMutation.mutate();
  };

  useEffect(() => {
    if (!idValid) {
      router.replace('/orders');
      return;
    }
    if (authLoading) return;
    if (hasToken) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(`/orders/${id}`)}`);
    }
  }, [authLoading, hasToken, isAuthenticated, router, id, idValid]);

  if (!idValid) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (authLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

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
        <Link
          href="/orders"
          className="inline-flex items-center justify-center rounded-full bg-[var(--color-brand)] px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--color-brand-muted)]"
        >
          Вернуться к заказам
        </Link>
      </div>
    );
  }

  return (
    <OrderDetail order={data} onReorder={handleReorder} isReordering={reorderMutation.isPending} />
  );
}
