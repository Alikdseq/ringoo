'use client';

import type { ReactElement } from 'react';
import { useState } from 'react';
import { Loader2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  initiateOrderPayment,
  takePayPhone,
} from '@/lib/api/services/payments.service';
import { getFriendlyErrorMessage } from '@/lib/errors';

export default function PaymentFailPage(): ReactElement {
  const params = useParams();
  const router = useRouter();
  const orderId = String(params?.id ?? '');
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  async function handleRetryPay(): Promise<void> {
    if (!orderId || retrying) return;
    setRetrying(true);
    setRetryError(null);
    try {
      const phone = takePayPhone(orderId);
      const result = await initiateOrderPayment(
        orderId,
        phone ? { phone } : undefined
      );
      if (result.form_url) {
        window.location.href = result.form_url;
        return;
      }
      setRetryError('Банк не вернул ссылку на оплату. Попробуйте позже.');
    } catch (err) {
      setRetryError(getFriendlyErrorMessage(err));
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-lg px-4 py-12 sm:px-6">
      <Card className="space-y-4 p-6 text-center">
        <XCircle className="mx-auto h-12 w-12 text-red-500" />
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          Оплата не завершена
        </h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Платёж отменён или не прошёл. Заказ сохранён — вы можете повторить оплату, пока не истёк
          срок резерва, либо оформить заказ заново.
        </p>
        {retryError && (
          <p className="text-sm text-red-600" role="alert">
            {retryError}
          </p>
        )}
        <div className="flex flex-wrap justify-center gap-2 pt-2">
          {orderId && (
            <Button
              type="button"
              disabled={retrying}
              onClick={() => {
                void handleRetryPay();
              }}
            >
              {retrying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Создаём платёж…
                </>
              ) : (
                'Оплатить снова'
              )}
            </Button>
          )}
          {orderId && (
            <Button asChild variant="outline">
              <Link href={`/orders/${orderId}/payment/return`}>Проверить статус</Link>
            </Button>
          )}
          <Button asChild variant="outline">
            <Link href="/checkout">Вернуться к оформлению</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/order-status">Статус заказа</Link>
          </Button>
        </div>
        {orderId && (
          <button
            type="button"
            className="text-xs text-zinc-400 underline"
            onClick={() => router.push(`/orders/${orderId}`)}
          >
            Открыть заказ
          </button>
        )}
      </Card>
    </div>
  );
}
