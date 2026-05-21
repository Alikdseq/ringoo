'use client';

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, usePathname } from 'next/navigation';
import { checkStaffAccess } from '@/lib/api/services/auth.service';
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
  const staffQueryEnabled =
    Boolean(isAuthenticated && !isLoginPage && pathname?.startsWith('/admin'));

  const {
    data: staffOk,
    isLoading: staffLoading,
    isFetching,
    isError: staffError,
  } = useQuery({
    queryKey: AUTH_STAFF_ACCESS_QUERY_KEY,
    queryFn: () => checkStaffAccess(),
    enabled: staffQueryEnabled,
    retry: false,
  });

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
      (staffOk === false || staffError)
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

  if (staffQueryEnabled && (staffLoading || isFetching || staffOk === undefined)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <Loading />
      </div>
    );
  }

  if (staffQueryEnabled && (staffOk === false || staffError)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-100">
        <Loading />
      </div>
    );
  }

  return <AdminLayout>{children}</AdminLayout>;
}
