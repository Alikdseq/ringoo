'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Clipboard } from 'lucide-react';
import { getOrders } from '@/lib/api/services/orders.service';
import { useAuth } from '@/lib/hooks/useAuth';
import { copyToClipboard } from '@/lib/clipboard';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { formatRuDateShort } from '@/lib/format-date';

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  confirmed: 'Подтверждён',
  in_progress: 'В работе',
  completed: 'Выполнен',
  cancelled: 'Отменён',
};

export default function OrdersPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const handleCopyOrderNumber = async (orderNumber: string) => {
    const ok = await copyToClipboard(orderNumber);
    setCopyFeedback(ok ? 'Номер скопирован' : 'Не удалось скопировать');
    window.setTimeout(() => setCopyFeedback(null), 2000);
  };

  const { data, isLoading, isError } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getOrders(),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent('/orders')}`);
    }
  }, [authLoading, isAuthenticated, router]);

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

  if (isError) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
        <p className="mb-4 text-danger">Не удалось загрузить заказы.</p>
        <Button asChild>
          <Link href="/profile">В профиль</Link>
        </Button>
      </div>
    );
  }

  const orders = data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
      <nav
        className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
        aria-label="Хлебные крошки"
      >
        <Link href="/" className="hover:text-foreground">
          Главная
        </Link>
        <span aria-hidden>/</span>
        <Link href="/profile" className="hover:text-foreground">
          Профиль
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Заказы</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold text-foreground">Мои заказы</h1>
      {copyFeedback ? (
        <p className="mb-4 text-sm text-brand" role="status">
          {copyFeedback}
        </p>
      ) : null}

      {orders.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="mb-4 text-foreground-muted">У вас пока нет заказов.</p>
          <Button asChild>
            <Link href="/catalog">В каталог</Link>
          </Button>
        </Card>
      ) : (
        <ul className="space-y-4">
          {orders.map(order => (
            <li key={order.id}>
              <Card className="relative p-4 transition-colors hover:bg-zinc-50">
                <Link
                  href={`/orders/${order.id}`}
                  className="absolute inset-0 rounded-[inherit]"
                  aria-label={`Заказ ${order.order_number}`}
                />
                <div className="pointer-events-none relative flex flex-wrap items-center justify-between gap-4">
                  <div className="flex min-w-0 flex-1 items-start gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-foreground">Заказ {order.order_number}</p>
                      <p className="text-sm text-foreground-muted">
                        {formatRuDateShort(order.created_at)}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="pointer-events-auto relative z-10 shrink-0 px-3"
                      aria-label={`Скопировать номер заказа ${order.order_number}`}
                      onClick={() => void handleCopyOrderNumber(order.order_number)}
                    >
                      <Clipboard className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-foreground">
                      {order.total_amount} {CURRENCY_SYMBOL}
                    </p>
                    <span className="inline-flex rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-foreground-muted">
                      {STATUS_LABELS[order.status] ?? order.status}
                    </span>
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
