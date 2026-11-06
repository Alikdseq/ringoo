'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { apiClient } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';

type ReturnRow = {
  id: string;
  number: string;
  order_number: string;
  status: string;
  ground: string;
  requested_refund_amount: string;
  created_at: string;
  items_count: number;
};

export default function AdminReturnsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'returns'],
    queryFn: async () => {
      const { data } = await apiClient.get<ReturnRow[]>('/admin/returns/');
      return data;
    },
  });

  if (isLoading) return <Loading />;
  if (error) {
    return <p className="p-6 text-sm text-red-600">Не удалось загрузить возвраты</p>;
  }

  return (
    <div className="space-y-4 p-6">
      <h1 className="text-2xl font-semibold text-zinc-900">Возвраты</h1>
      <p className="text-sm text-zinc-600">
        Заявки покупателей. Денежный возврат и склад разделены; restock только после проверки.
      </p>
      <Card className="overflow-x-auto p-0">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-zinc-200 bg-zinc-50 text-zinc-600">
            <tr>
              <th className="px-4 py-3">Номер</th>
              <th className="px-4 py-3">Заказ</th>
              <th className="px-4 py-3">Основание</th>
              <th className="px-4 py-3">Сумма</th>
              <th className="px-4 py-3">Статус</th>
              <th className="px-4 py-3">Дата</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map(row => (
              <tr key={row.id} className="border-b border-zinc-100">
                <td className="px-4 py-3">
                  <Link className="text-[var(--color-brand)] underline" href={`/admin/returns/${row.id}`}>
                    {row.number}
                  </Link>
                </td>
                <td className="px-4 py-3">{row.order_number}</td>
                <td className="px-4 py-3">{row.ground}</td>
                <td className="px-4 py-3">{row.requested_refund_amount}</td>
                <td className="px-4 py-3">{row.status}</td>
                <td className="px-4 py-3">{new Date(row.created_at).toLocaleString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data?.length ? (
          <p className="p-4 text-sm text-zinc-500">Заявок пока нет</p>
        ) : null}
      </Card>
    </div>
  );
}
