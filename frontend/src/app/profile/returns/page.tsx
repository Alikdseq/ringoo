'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { isReturnsUiEnabled } from '@/lib/features/returns';

export default function ProfileReturnsPage() {
  const enabled = isReturnsUiEnabled();

  const { data, isLoading, error } = useQuery({
    queryKey: ['returns', 'mine'],
    enabled,
    queryFn: async () => {
      const { data } = await apiClient.get('/returns/');
      return data as Array<{ id: string; number: string; status: string; created_at: string }>;
    },
  });

  if (!enabled) {
    notFound();
  }

  if (isLoading) return <Loading />;
  if (error) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm text-red-600">
        Не удалось загрузить заявки. Войдите в аккаунт.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Мои возвраты</h1>
      <p className="text-sm text-zinc-600">
        Оформить возврат можно из карточки заказа. Статусы заявок отображаются ниже.
      </p>
      {(data || []).map(row => (
        <Card key={row.id} className="p-4 text-sm">
          <Link href={`/profile/returns/${row.id}`} className="font-medium text-[var(--color-brand)]">
            {row.number}
          </Link>
          <p className="text-zinc-600">{row.status}</p>
          <p className="text-zinc-500">{new Date(row.created_at).toLocaleString('ru-RU')}</p>
        </Card>
      ))}
      {!data?.length ? <p className="text-sm text-zinc-500">Заявок пока нет</p> : null}
    </div>
  );
}
