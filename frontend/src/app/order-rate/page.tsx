'use client';

import { Suspense, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Star } from 'lucide-react';
import { getManagers } from '@/lib/api/services/stores.service';
import { submitOrderRating } from '@/lib/api/services/orders.service';
import { useAuth } from '@/lib/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { cn } from '@/lib/theme/utils';

function getRatingErrorMessage(error: unknown): string {
  if (error && typeof error === 'object') {
    const obj = error as { response?: { data?: { detail?: string } }; message?: string };
    if (typeof obj?.response?.data?.detail === 'string') return obj.response.data.detail;
    if (typeof obj?.message === 'string') return obj.message;
  }
  return 'Не удалось отправить оценку.';
}

function OrderRateContent() {
  const searchParams = useSearchParams();
  const orderFromUrl = searchParams.get('order') ?? '';
  const orderIdFromUrl = searchParams.get('order_id') ?? '';
  const managerIdFromUrl = searchParams.get('manager_id') ?? '';

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [orderNumber, setOrderNumber] = useState(orderFromUrl);
  const [phone, setPhone] = useState('');
  const [managerId, setManagerId] = useState(managerIdFromUrl);
  const [rating, setRating] = useState<number>(0);
  const [comment, setComment] = useState('');

  const {
    data: managers = [],
    isLoading: managersLoading,
    isError: managersError,
    refetch: refetchManagers,
  } = useQuery({
    queryKey: ['managers'],
    queryFn: getManagers,
  });

  const managersByStore = useMemo(() => {
    const map = new Map<string, typeof managers>();
    for (const m of managers) {
      const key = m.store.id;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    return Array.from(map.entries()).map(([storeId, list]) => ({
      storeName: list[0]!.store.name,
      storeCity: list[0]!.store.city,
      managers: list,
    }));
  }, [managers]);

  const useOrderId = Boolean(orderIdFromUrl && isAuthenticated);

  const mutation = useMutation({
    mutationFn: submitOrderRating,
    onSuccess: () => setSuccess(true),
  });

  const [success, setSuccess] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!managerId || rating < 1) return;
    const payload = {
      manager_id: managerId,
      rating,
      comment: comment || undefined,
    };
    if (useOrderId) {
      mutation.mutate({ ...payload, order_id: orderIdFromUrl });
    } else {
      if (!orderNumber.trim() || !phone.trim()) return;
      mutation.mutate({
        ...payload,
        order_number: orderNumber.trim(),
        phone: phone.trim(),
      });
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (success) {
    return (
      <div className="mx-auto w-full max-w-xl px-4 py-10 sm:px-6 lg:px-8">
        <Card className="p-8 text-center">
          <p className="mb-4 text-lg font-medium text-foreground">Спасибо! Ваша оценка учтена.</p>
          <Button asChild>
            <Link href="/">На главную</Link>
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-xl px-4 py-10 sm:px-6 lg:px-8">
      <nav
        className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
        aria-label="Хлебные крошки"
      >
        <Link href="/" className="hover:text-foreground">
          Главная
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Оценка заказа</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold text-foreground">Оцените работу менеджера</h1>
      <p className="mb-6 text-sm text-foreground-muted">
        Выберите менеджера, который вас обслуживал, и поставьте оценку.
      </p>

      <form onSubmit={handleSubmit}>
        <Card className="space-y-4 p-6">
          {useOrderId ? (
            <p className="text-sm text-foreground-muted">
              Заказ для оценки выбран из вашего профиля.
            </p>
          ) : (
            <>
              <div>
                <label
                  htmlFor="rate-order-number"
                  className="mb-1 block text-sm text-foreground-muted"
                >
                  Номер заказа <span className="text-danger">*</span>
                </label>
                <Input
                  id="rate-order-number"
                  value={orderNumber}
                  onChange={e => setOrderNumber(e.target.value)}
                  placeholder="ORD-20250208-abc123"
                  required
                />
              </div>
              <div>
                <label htmlFor="rate-phone" className="mb-1 block text-sm text-foreground-muted">
                  Телефон <span className="text-danger">*</span>
                </label>
                <Input
                  id="rate-phone"
                  type="tel"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="+7 (999) 123-45-67"
                  required
                />
              </div>
            </>
          )}

          <div>
            <label htmlFor="rate-manager" className="mb-1 block text-sm text-foreground-muted">
              Менеджер, который вас обслуживал <span className="text-danger">*</span>
            </label>
            {managersLoading ? (
              <p className="text-sm text-foreground-muted">Загрузка списка менеджеров…</p>
            ) : managersError ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <p className="mb-2">Не удалось загрузить список менеджеров.</p>
                <Button variant="outline" size="sm" onClick={() => refetchManagers()}>
                  Повторить
                </Button>
              </div>
            ) : managersByStore.length === 0 ? (
              <p className="text-sm text-foreground-muted">
                Список менеджеров пуст. Обратитесь в поддержку.
              </p>
            ) : (
              <select
                id="rate-manager"
                value={managerId}
                onChange={e => setManagerId(e.target.value)}
                required
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:bg-zinc-900"
              >
                <option value="">Выберите менеджера</option>
                {managersByStore.map(({ storeName, storeCity, managers: list }) => (
                  <optgroup
                    key={storeName}
                    label={`${storeName}${storeCity ? `, ${storeCity}` : ''}`}
                  >
                    {list.map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            )}
          </div>

          <div>
            <span className="mb-2 block text-sm text-foreground-muted">
              Оценка <span className="text-danger">*</span>
            </span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map(v => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setRating(v)}
                  className={cn(
                    'rounded p-2 transition-colors',
                    rating >= v ? 'text-amber-500' : 'text-zinc-300 hover:text-zinc-400'
                  )}
                  aria-label={`Оценка ${v}`}
                >
                  <Star className={cn('h-8 w-8', rating >= v && 'fill-current')} />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="rate-comment" className="mb-1 block text-sm text-foreground-muted">
              Комментарий (необязательно)
            </label>
            <textarea
              id="rate-comment"
              value={comment}
              onChange={e => setComment(e.target.value)}
              rows={3}
              maxLength={2000}
              className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary dark:bg-zinc-900"
            />
          </div>

          {mutation.isError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              {getRatingErrorMessage(mutation.error)}
            </p>
          )}

          <Button type="submit" disabled={mutation.isPending || rating < 1 || !managerId}>
            {mutation.isPending ? 'Отправка…' : 'Отправить оценку'}
          </Button>
        </Card>
      </form>
    </div>
  );
}

export default function OrderRatePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-[var(--color-brand)] border-t-transparent" />
        </div>
      }
    >
      <OrderRateContent />
    </Suspense>
  );
}
