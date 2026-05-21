'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import {
  getAdminMissingProductRequests,
  updateAdminMissingProductStatus,
  type AdminMissingProductRequest,
  type AdminMissingProductParams,
} from '@/lib/api/services/adminCrm.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

export default function AdminCrmPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<'' | 'new' | 'processed' | 'closed'>('');

  const params: AdminMissingProductParams = {
    page,
    status: status || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'crm', 'missing-product', params],
    queryFn: () => getAdminMissingProductRequests(params),
  });

  const updateStatusMutation = useMutation({
    mutationFn: (variables: { id: string; status: string }) =>
      updateAdminMissingProductStatus(variables.id, variables.status),
    onSuccess: () => {
      void refetch();
    },
  });

  const requests: AdminMissingProductRequest[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = requests.length > 0 ? requests.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Заявки «Не нашли товар»</h1>
        <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Обновить
        </Button>
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Статус заявки</label>
            <select
              value={status}
              onChange={e => {
                setStatus(e.target.value as '' | 'new' | 'processed' | 'closed');
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              <option value="new">Новые</option>
              <option value="processed">В работе</option>
              <option value="closed">Закрытые</option>
            </select>
          </div>
          <div className="text-xs text-zinc-500">
            Показано {requests.length} из {total} заявок.
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить заявки.</div>
        ) : requests.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Заявок по текущему фильтру нет.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Товар</th>
                  <th className="px-3 py-2 text-left">Контакт</th>
                  <th className="px-3 py-2 text-left">Телефон</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Комментарий</th>
                  <th className="px-3 py-2 text-left">Статус</th>
                  <th className="px-3 py-2 text-left">Дата</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {requests.map(req => {
                  const createdAt = new Date(req.created_at);
                  const created = !Number.isNaN(createdAt.getTime())
                    ? createdAt.toLocaleString()
                    : '';
                  return (
                    <tr key={req.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{req.product_name}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{req.contact_name || '—'}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{req.contact_phone}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {req.contact_email || '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{req.comment || '—'}</td>
                      <td className="px-3 py-2 text-xs">
                        {req.status === 'new' && (
                          <span className="rounded-full bg-sky-50 px-2 py-0.5 text-sky-700">
                            Новая
                          </span>
                        )}
                        {req.status === 'processed' && (
                          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">
                            В работе
                          </span>
                        )}
                        {req.status === 'closed' && (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Закрыта
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{created}</td>
                      <td className="px-3 py-2 text-right text-xs">
                        {req.status !== 'new' && (
                          <button
                            type="button"
                            className="mr-2 text-[var(--color-brand)] hover:underline"
                            onClick={() =>
                              updateStatusMutation.mutate({
                                id: req.id,
                                status: 'new',
                              })
                            }
                            disabled={updateStatusMutation.isPending}
                          >
                            В новую
                          </button>
                        )}
                        {req.status !== 'processed' && (
                          <button
                            type="button"
                            className="mr-2 text-[var(--color-brand)] hover:underline"
                            onClick={() =>
                              updateStatusMutation.mutate({
                                id: req.id,
                                status: 'processed',
                              })
                            }
                            disabled={updateStatusMutation.isPending}
                          >
                            В работу
                          </button>
                        )}
                        {req.status !== 'closed' && (
                          <button
                            type="button"
                            className="text-[var(--color-brand)] hover:underline"
                            onClick={() =>
                              updateStatusMutation.mutate({
                                id: req.id,
                                status: 'closed',
                              })
                            }
                            disabled={updateStatusMutation.isPending}
                          >
                            Закрыть
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-zinc-600">
          <div>
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              Назад
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
