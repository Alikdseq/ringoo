'use client';

import type { ReactElement } from 'react';
import { useEffect, useSyncExternalStore } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  getOrderPaymentStatus,
  takePayAuth,
  type PayGuestAuth,
} from '@/lib/api/services/payments.service';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { useAuth } from '@/lib/hooks/useAuth';

function subscribePayAuthStore(_onStoreChange: () => void): () => void {
  return () => {};
}

function readPayAuthSnapshot(orderId: string): PayGuestAuth | null {
  if (!orderId) return null;
  return takePayAuth(orderId);
}

/**
 * Return URL после оплаты (ЮKassa / Сбер).
 * Успех подтверждается только через API сайта → сверка со шлюзом на backend.
 * Возврат по URL сам по себе не означает оплату.
 * Корзина на backend очищается только при status=paid; здесь лишь инвалидируем кэш.
 *
 * B8-005: гость без sessionStorage stash не дергает payment API (403) —
 * показываем восстановление через /order-status (SEC-006), без токена в URL.
 */
export default function PaymentReturnPage(): ReactElement {
  const params = useParams();
  const orderId = String(params?.id ?? '');
  const queryClient = useQueryClient();
  const { isAuthenticated, isLoading: authLoading, hasToken } = useAuth();
  // Client-only sessionStorage; SSR snapshot = null (без hydration mismatch).
  const guestAuth = useSyncExternalStore(
    subscribePayAuthStore,
    () => readPayAuthSnapshot(orderId),
    () => null
  );

  const canQueryPayment =
    Boolean(orderId) &&
    !authLoading &&
    (isAuthenticated || hasToken || Boolean(guestAuth?.guest_token));

  const missingGuestAccess =
    !authLoading &&
    !isAuthenticated &&
    !hasToken &&
    !guestAuth?.guest_token;

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: [
      'order-payment',
      orderId,
      guestAuth?.phone,
      guestAuth?.order_number,
      guestAuth?.guest_token,
      isAuthenticated,
    ],
    queryFn: () =>
      getOrderPaymentStatus(
        orderId,
        guestAuth
          ? {
              phone: guestAuth.phone,
              order_number: guestAuth.order_number,
              guest_token: guestAuth.guest_token,
            }
          : undefined
      ),
    enabled: canQueryPayment,
    refetchInterval: query => {
      const status = query.state.data?.payment?.status;
      if (
        status === 'paid' ||
        status === 'failed' ||
        status === 'expired' ||
        status === 'reversed' ||
        status === 'refunded' ||
        status === 'needs_review'
      ) {
        return false;
      }
      return 3000;
    },
    retry: 2,
  });

  const paid = data?.payment?.status === 'paid';
  const needsReview = data?.payment?.status === 'needs_review';
  const failed =
    data?.payment?.status === 'failed' ||
    data?.payment?.status === 'expired' ||
    data?.payment?.status === 'reversed' ||
    data?.payment?.status === 'refunded';

  useEffect(() => {
    if (!paid) return;
    void queryClient.invalidateQueries({ queryKey: ['cart'] });
    void queryClient.invalidateQueries({ queryKey: ['orders'] });
  }, [paid, queryClient]);

  if (missingGuestAccess) {
    const orderNumberHint = guestAuth?.order_number;
    return (
      <div className="mx-auto w-full max-w-lg px-4 py-12 sm:px-6">
        <Card className="space-y-4 p-6 text-center">
          <XCircle className="mx-auto h-12 w-12 text-amber-500" />
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
            Нужен доступ к заказу
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            Данные для проверки оплаты в этой вкладке не найдены (другой браузер, режим
            инкогнито или очищенное хранилище). Номер заказа сам по себе не открывает
            персональные данные — восстановите доступ по телефону и письму.
          </p>
          <div className="flex flex-wrap justify-center gap-2 pt-2">
            <Button asChild>
              <Link
                href={
                  orderNumberHint
                    ? `/order-status?order_number=${encodeURIComponent(orderNumberHint)}`
                    : '/order-status'
                }
              >
                Статус заказа
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/catalog">В каталог</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-12 sm:px-6">
      <Card className="space-y-4 p-6 text-center">
        {(authLoading || isLoading || isFetching) && !paid && !failed && !needsReview && (
          <>
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-brand" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Проверяем оплату…
            </h1>
            <p className="text-sm text-zinc-500">
              Не закрывайте страницу. Статус сверяется с платёжной системой.
            </p>
          </>
        )}

        {paid && (
          <>
            <CheckCircle2 className="mx-auto h-12 w-12 text-brand" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Оплата прошла успешно
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              Заказ {data?.payment.order_number}. Сумма:{' '}
              {data?.payment.amount} {CURRENCY_SYMBOL}.
            </p>
            <Button asChild className="mt-2">
              <Link href={`/orders/${orderId}`}>К заказу</Link>
            </Button>
          </>
        )}

        {needsReview && !paid && (
          <>
            <Loader2 className="mx-auto h-12 w-12 text-amber-500" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Платёж на проверке
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              Оплата обрабатывается. Не создавайте повторный платёж. Сохраните номер
              заказа и при необходимости свяжитесь с поддержкой.
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => refetch()}>
                Проверить ещё раз
              </Button>
              <Button asChild>
                <Link href={`/orders/${orderId}`}>К заказу</Link>
              </Button>
            </div>
          </>
        )}

        {(failed || isError) && !paid && !needsReview && (
          <>
            <XCircle className="mx-auto h-12 w-12 text-red-500" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Оплата не подтверждена
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              {isError
                ? getFriendlyErrorMessage(error)
                : 'Банк не подтвердил успешную оплату. Если средства списаны — обратитесь в поддержку, приложив номер заказа.'}
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => refetch()}>
                Проверить ещё раз
              </Button>
              <Button asChild>
                <Link href={`/orders/${orderId}/payment/fail`}>К ошибке оплаты</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/order-status">Статус заказа</Link>
              </Button>
            </div>
          </>
        )}

        {!authLoading &&
          !isLoading &&
          !paid &&
          !failed &&
          !needsReview &&
          !isError &&
          data && (
          <>
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-brand" />
            <h1 className="text-xl font-semibold">Ожидаем подтверждение оплаты</h1>
            <p className="text-sm text-zinc-500">
              Статус платежа: {data.payment.status}. Обновляем автоматически…
            </p>
            <Button type="button" variant="outline" onClick={() => refetch()}>
              Обновить сейчас
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
