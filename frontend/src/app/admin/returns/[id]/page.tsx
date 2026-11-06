'use client';

import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { useState } from 'react';

export default function AdminReturnDetailPage() {
  const params = useParams();
  const id = String(params?.id || '');
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'returns', id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data } = await apiClient.get(`/admin/returns/${id}/`);
      return data;
    },
  });

  const transition = useMutation({
    mutationFn: async (status: string) => {
      const { data } = await apiClient.post(`/admin/returns/${id}/transition/`, { status });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'returns', id] }),
    onError: (e) => setError(getFriendlyErrorMessage(e)),
  });

  const refund = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post(`/admin/returns/${id}/refund/`, { dry_run: true });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'returns', id] }),
    onError: (e) => setError(getFriendlyErrorMessage(e)),
  });

  if (isLoading || !data) return <Loading />;

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">{data.number}</h1>
      <Card className="space-y-2 p-4 text-sm">
        <p>Заказ: {data.order_number}</p>
        <p>Статус: {data.status}</p>
        <p>Основание: {data.ground}</p>
        <p>Сумма: {data.requested_refund_amount}</p>
        <p>{data.description}</p>
      </Card>
      <Card className="space-y-2 p-4 text-sm">
        <h2 className="font-medium">Позиции</h2>
        {(data.items || []).map((it: { id: string; product_title: string; quantity: number; color_label: string; condition: string }) => (
          <div key={it.id}>
            {it.product_title} × {it.quantity} {it.color_label ? `(${it.color_label})` : ''} — {it.condition}
          </div>
        ))}
      </Card>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={() => transition.mutate('under_review')}>В работу</Button>
        <Button type="button" onClick={() => transition.mutate('approved')}>Согласовать</Button>
        <Button type="button" onClick={() => transition.mutate('rejected')}>Отказать</Button>
        <Button type="button" onClick={() => refund.mutate()}>
          Возврат денег (dry-run)
        </Button>
      </div>
      <p className="text-xs text-zinc-500">
        Реальный вызов платёжного API отключён по умолчанию (dry_run). Restock — отдельным inspect после приёмки.
      </p>
    </div>
  );
}
