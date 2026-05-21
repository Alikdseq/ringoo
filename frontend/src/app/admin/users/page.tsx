'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import {
  getAdminUsers,
  updateAdminUser,
  type AdminUserListItem,
  type AdminUserListParams,
} from '@/lib/api/services/adminUsers.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

export default function AdminUsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  const params: AdminUserListParams = {
    page,
    search: search || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => getAdminUsers(params),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (user: AdminUserListItem) =>
      updateAdminUser(user.id, { is_active: !user.is_active }),
    onSuccess: () => {
      void refetch();
    },
  });

  const users: AdminUserListItem[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = users.length > 0 ? users.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Пользователи</h1>
        <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Обновить
        </Button>
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1 sm:max-w-xs">
            <label className="block text-xs font-medium text-zinc-500">
              Поиск по телефону, email или имени
            </label>
            <input
              type="text"
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="+7..., email или имя"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch('');
              setPage(1);
            }}
          >
            Сбросить фильтр
          </Button>
        </div>

        <div className="mt-3 text-xs text-zinc-500">
          Показано {users.length} из {total} пользователей.
        </div>
      </Card>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[260px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить пользователей.</div>
        ) : users.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Пользователи не найдены.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Телефон</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Роль</th>
                  <th className="px-3 py-2 text-left">Дата регистрации</th>
                  <th className="px-3 py-2 text-center">Активен</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => {
                  const createdAt = new Date(user.created_at);
                  const created =
                    Number.isNaN(createdAt.getTime()) === false
                      ? createdAt.toLocaleDateString()
                      : '';
                  return (
                    <tr
                      key={user.id}
                      className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                    >
                      <td className="px-3 py-2 align-middle text-sm text-zinc-900">
                        <Link
                          href={`/admin/users/${user.id}`}
                          className="text-[var(--color-brand)] hover:underline"
                        >
                          {user.phone}
                        </Link>
                      </td>
                      <td className="px-3 py-2 align-middle text-xs text-zinc-600">
                        {user.email || '—'}
                      </td>
                      <td className="px-3 py-2 align-middle text-xs text-zinc-600">
                        {user.is_staff ? 'Админ' : 'Пользователь'}
                      </td>
                      <td className="px-3 py-2 align-middle text-xs text-zinc-600">{created}</td>
                      <td className="px-3 py-2 align-middle text-center text-xs">
                        {user.is_active ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Активен
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Заблокирован
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 align-middle text-right text-xs">
                        <button
                          type="button"
                          className="text-[var(--color-brand)] hover:underline"
                          onClick={() => toggleActiveMutation.mutate(user)}
                          disabled={toggleActiveMutation.isPending}
                        >
                          {user.is_active ? 'Заблокировать' : 'Разблокировать'}
                        </button>
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
