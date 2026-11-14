'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { useRouter, usePathname } from 'next/navigation';
import { fetchStaffAccess } from '@/lib/api/services/auth.service';
import { useAuth, AUTH_STAFF_ACCESS_QUERY_KEY } from '@/lib/hooks/useAuth';
import { getApiErrorStatus, getFriendlyErrorMessage } from '@/lib/errors';
import { Loading } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import { AdminLayout } from './AdminLayout';

function AdminGateShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-zinc-100 px-4 text-center">
      {children}
    </div>
  );
}

/**
 * B8-009: клиентский gate для /admin/* — не показывает AdminLayout/страницу
 * до подтверждённого staff-access. Backend RBAC остаётся источником истины.
 *
 * Состояния: loading | unauthenticated → login | forbidden (403) |
 * unavailable (5xx/сеть) + retry | staff → AdminLayout.
 * На /admin/login — дети без layout.
 */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading: authLoading, isAuthenticated, hasToken } = useAuth();

  const isLoginPage = pathname === '/admin/login';
  const staffQueryEnabled = Boolean(
    isAuthenticated && !isLoginPage && pathname?.startsWith('/admin')
  );

  const {
    data: staffAccess,
    isLoading: staffLoading,
    isFetching,
    isError: staffError,
    error: staffQueryError,
    refetch: refetchStaff,
    isSuccess: staffSuccess,
  } = useQuery({
    queryKey: AUTH_STAFF_ACCESS_QUERY_KEY,
    queryFn: () => fetchStaffAccess(),
    enabled: staffQueryEnabled,
    retry: false,
    staleTime: 60_000,
  });

  const staffStatus = getApiErrorStatus(staffQueryError);
  const staffOk = staffSuccess && staffAccess?.staff === true;
  const staffForbidden = staffError && (staffStatus === 403 || staffStatus === 401);
  const staffUnavailable = staffError && !staffForbidden;

  useEffect(() => {
    if (authLoading || isLoginPage) return;

    if (!isAuthenticated || !user) {
      router.replace(`/admin/login?next=${encodeURIComponent(pathname ?? '/admin')}`);
      return;
    }

    // Истечение сессии на staff-access → снова login (не «гостевой» home).
    if (staffQueryEnabled && staffError && staffStatus === 401) {
      router.replace(`/admin/login?next=${encodeURIComponent(pathname ?? '/admin')}`);
    }
  }, [
    authLoading,
    isAuthenticated,
    user,
    isLoginPage,
    pathname,
    router,
    staffQueryEnabled,
    staffError,
    staffStatus,
  ]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  // Пока auth/me не готов — только нейтральный shell (без AdminLayout / children).
  if (authLoading || (!isAuthenticated && hasToken)) {
    return (
      <AdminGateShell>
        <Loading />
        <p className="text-sm text-zinc-500">Проверяем сессию…</p>
      </AdminGateShell>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <AdminGateShell>
        <Loading />
        <p className="text-sm text-zinc-500">Переход ко входу…</p>
      </AdminGateShell>
    );
  }

  // Staff-access ещё не settled — не рендерим админ-контент (нет мерцания shell).
  if (staffQueryEnabled && (staffLoading || (isFetching && !staffSuccess && !staffError))) {
    return (
      <AdminGateShell>
        <Loading />
        <p className="text-sm text-zinc-500">Проверяем доступ…</p>
      </AdminGateShell>
    );
  }

  if (staffQueryEnabled && staffError && staffStatus === 401) {
    return (
      <AdminGateShell>
        <Loading />
        <p className="text-sm text-zinc-500">Сессия истекла. Переход ко входу…</p>
      </AdminGateShell>
    );
  }

  if (staffQueryEnabled && (staffForbidden || (staffSuccess && !staffOk))) {
    return (
      <AdminGateShell>
        <h1 className="text-xl font-semibold text-zinc-900">Доступ запрещён</h1>
        <p className="max-w-md text-sm text-zinc-600">
          {staffStatus === 403
            ? getFriendlyErrorMessage(staffQueryError)
            : 'У вашей учётной записи нет прав администратора. Админ-панель недоступна.'}
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          <Button asChild>
            <Link href="/">На главную</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href={`/admin/login?next=${encodeURIComponent(pathname ?? '/admin')}`}>
              Войти как сотрудник
            </Link>
          </Button>
        </div>
      </AdminGateShell>
    );
  }

  // 5xx / сеть: не считать гостем и не открывать админку.
  if (staffQueryEnabled && staffUnavailable) {
    return (
      <AdminGateShell>
        <h1 className="text-xl font-semibold text-zinc-900">Не удалось проверить доступ</h1>
        <p className="max-w-md text-sm text-zinc-600">
          {getFriendlyErrorMessage(staffQueryError)}
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          <Button
            type="button"
            onClick={() => {
              void refetchStaff();
            }}
          >
            Повторить
          </Button>
          <Button asChild variant="outline">
            <Link href="/">На главную</Link>
          </Button>
        </div>
      </AdminGateShell>
    );
  }

  if (!staffOk || !staffAccess) {
    return (
      <AdminGateShell>
        <Loading />
      </AdminGateShell>
    );
  }

  return <AdminLayout staffAccess={staffAccess}>{children}</AdminLayout>;
}
