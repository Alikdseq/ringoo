'use client';

import type { ReactElement } from 'react';
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  getOrderPaymentStatus,
  takePayPhone,
} from '@/lib/api/services/payments.service';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getFriendlyErrorMessage } from '@/lib/errors';

/**
 * Return URL после оплаты на стороне Сбера.
 * Успех подтверждается только через API сайта → getOrderStatusExtended на backend.
 */
export default function PaymentReturnPage(): ReactElement {
  const params = useParams();
  const orderId = String(params?.id ?? '');
  const [phone, setPhone] = useState<string | null>(null);

  useEffect(() => {
    if (orderId) setPhone(takePayPhone(orderId));
  }, [orderId]);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['order-payment', orderId, phone],
    queryFn: () =>
      getOrderPaymentStatus(orderId, phone ? { phone } : undefined),
    enabled: Boolean(orderId),
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
  const failed =
    data?.payment?.status === 'failed' ||
    data?.payment?.status === 'expired' ||
    data?.payment?.status === 'reversed' ||
    data?.payment?.status === 'refunded' ||
    data?.payment?.status === 'needs_review';

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-12 sm:px-6">
      <Card className="space-y-4 p-6 text-center">
        {(isLoading || isFetching) && !paid && !failed && (
          <>
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-brand" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              Проверяем оплату…
            </h1>
            <p className="text-sm text-zinc-500">
              Не закрывайте страницу. Статус запрашивается у банка.
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

        {(failed || isError) && !paid && (
          <>
            <XCircle className="mx-auto h-12 w-12 text-red-500" />
            <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
              {data?.payment?.status === 'needs_review'
                ? 'Платёж на проверке'
                : 'Оплата не подтверждена'}
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              {isError
                ? getFriendlyErrorMessage(error)
                : data?.payment?.status === 'needs_review'
                  ? 'Оплата получена банком, но заказ требует ручной сверки. Сохраните номер заказа и свяжитесь с поддержкой.'
                  : 'Банк не подтвердил успешную оплату. Если средства списаны — обратитесь в поддержку, приложив номер заказа.'}
            </p>
            <div className="flex flex-wrap justify-center gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => refetch()}>
                Проверить ещё раз
              </Button>
              {data?.payment?.status !== 'needs_review' && (
                <Button asChild>
                  <Link href={`/orders/${orderId}/payment/fail`}>К ошибке оплаты</Link>
                </Button>
              )}
            </div>
          </>
        )}

        {!isLoading && !paid && !failed && !isError && data && (
          <>
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-brand" />
            <h1 className="text-xl font-semibold">Ожидаем подтверждение банка</h1>
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
