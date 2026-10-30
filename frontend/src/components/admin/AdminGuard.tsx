'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, usePathname } from 'next/navigation';
import { fetchStaffAccess } from '@/lib/api/services/auth.service';
import { useAuth, AUTH_STAFF_ACCESS_QUERY_KEY } from '@/lib/hooks/useAuth';
import { Loading } from '@/components/ui/Loading';
import { AdminLayout } from './AdminLayout';

/**
 * Проверяет: пользователь авторизован и имеет staff (отдельный запрос staff-access).
 * Не-staff перенаправляет на главную, неавторизованного — на /admin/login.
 * На /admin/login — рендерит детей без layout.
 */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();

  const isLoginPage = pathname === '/admin/login';
  const staffQueryEnabled = Boolean(
    isAuthenticated && !isLoginPage && pathname?.startsWith('/admin')
  );

  const {
    data: staffAccess,
    isLoading: staffLoading,
    isFetching,
    isError: staffError,
  } = useQuery({
    queryKey: AUTH_STAFF_ACCESS_QUERY_KEY,
    queryFn: () => fetchStaffAccess(),
    enabled: staffQueryEnabled,
    retry: false,
  });

  const staffOk = staffAccess?.staff === true;

  useEffect(() => {
    if (authLoading || isLoginPage) return;

    if (!isAuthenticated || !user) {
      router.replace(`/admin/login?next=${encodeURIComponent(pathname ?? '/admin')}`);
      return;
    }

    if (
      staffQueryEnabled &&
      !staffLoading &&
      !isFetching &&
      (staffAccess === null || staffOk === false || staffError)
    ) {
      router.replace('/');
    }
  }, [
    authLoading,
    isAuthenticated,
    user,
    isLoginPage,
    pathname,
    router,
    staffQueryEnabled,
    staffLoading,
    isFetching,
    staffAccess,
    staffOk,
    staffError,
  ]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  if (authLoading || !isAuthenticated || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <Loading />
      </div>
    );
  }

  if (staffQueryEnabled && (staffLoading || isFetching || staffAccess === undefined)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <Loading />
      </div>
    );
  }

  if (staffQueryEnabled && (!staffOk || staffError)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <Loading />
      </div>
    );
  }

  return <AdminLayout staffAccess={staffAccess}>{children}</AdminLayout>;
}
