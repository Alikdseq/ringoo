'use client';

import { useParams } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import {
  getAdminUser,
  updateAdminUser,
  type AdminUserDetail,
} from '@/lib/api/services/adminUsers.service';

interface RouteParams {
  id: string;
}

export default function AdminUserDetailPage() {
  const params = useParams() as unknown as RouteParams;
  const userId = params.id;

  const {
    data: user,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn: () => getAdminUser(userId),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { is_active?: boolean; is_staff?: boolean }) =>
      updateAdminUser(userId, payload),
    onSuccess: () => {
      void refetch();
    },
  });

  if (isLoading || !user) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Не удалось загрузить пользователя.
      </div>
    );
  }

  const fullName = [user.profile?.last_name, user.profile?.first_name, user.profile?.middle_name]
    .filter(Boolean)
    .join(' ');

  const createdAt = new Date(user.created_at);
  const created = Number.isNaN(createdAt.getTime()) === false ? createdAt.toLocaleString() : '';

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Пользователь</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {user.phone} {user.email ? `• ${user.email}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant={user.is_active ? 'outline' : 'primary'}
            size="sm"
            onClick={() => updateMutation.mutate({ is_active: !user.is_active })}
            disabled={updateMutation.isPending}
          >
            {user.is_active ? 'Заблокировать' : 'Разблокировать'}
          </Button>
          <Button
            type="button"
            variant={user.is_staff ? 'outline' : 'primary'}
            size="sm"
            onClick={() => updateMutation.mutate({ is_staff: !user.is_staff })}
            disabled={updateMutation.isPending}
          >
            {user.is_staff ? 'Снять права staff' : 'Выдать staff'}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1.4fr,1.2fr]">
        {/* Профиль и адреса */}
        <Card className="space-y-4 p-4">
          <h2 className="text-sm font-semibold text-zinc-900">Профиль</h2>
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-zinc-500">ФИО:</span>{' '}
              <span className="font-medium text-zinc-900">{fullName || '—'}</span>
            </div>
            <div>
              <span className="text-zinc-500">Дата регистрации:</span>{' '}
              <span className="text-zinc-900">{created}</span>
            </div>
            <div>
              <span className="text-zinc-500">Дата рождения:</span>{' '}
              <span className="text-zinc-900">{user.profile?.birth_date ?? '—'}</span>
            </div>
            <div>
              <span className="text-zinc-500">Пол:</span>{' '}
              <span className="text-zinc-900">{user.profile?.gender ?? '—'}</span>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Адреса доставки
            </h3>
            {user.delivery_addresses.length === 0 ? (
              <p className="text-sm text-zinc-500">Адреса ещё не добавлены.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {user.delivery_addresses.map(addr => (
                  <li key={addr.id} className="rounded-lg border border-zinc-200 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-zinc-900">{addr.title}</span>
                      {addr.is_default && (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-700">
                          Основной
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-zinc-600">
                      {addr.city}, {addr.street}, {addr.house}
                      {addr.apartment ? `, кв. ${addr.apartment}` : ''}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>

        <Card className="space-y-4 p-4">
          <h2 className="text-sm font-semibold text-zinc-900">Заказы</h2>
          <div className="text-sm">
            <span className="text-zinc-500">История заказов:</span>{' '}
            <Link
              href={`/admin/orders?search=${encodeURIComponent(user.phone)}`}
              className="text-[var(--color-brand)] hover:underline"
            >
              смотреть заказы пользователя
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
