import { useEffect, useLayoutEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { User } from '@/types';
import { authCookiesMode, hasAuthSessionFlag, hasAuthSessionHint } from '@/lib/auth-mode';
import { getMe, logoutAuth } from '@/lib/api/services/auth.service';
import { getAccessToken } from '@/lib/storage/token-storage';

export const AUTH_ME_QUERY_KEY = ['auth', 'me'] as const;

/** Проверка staff для /admin (отдельно от публичного /auth/me/). */
export const AUTH_STAFF_ACCESS_QUERY_KEY = ['auth', 'staff-access'] as const;

/** Загрузка текущего пользователя; экспорт для fetchQuery после login/register. */
export async function authMeQueryFn(): Promise<User | null> {
  try {
    return await getMe();
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 401) {
      await logoutAuth();
      return null;
    }
    throw err;
  }
}

function computeHasToken(): boolean {
  if (typeof window === 'undefined') return false;
  if (getAccessToken()) return true;
  if (authCookiesMode() && (hasAuthSessionHint() || hasAuthSessionFlag())) return true;
  return false;
}

export function useAuth() {
  const queryClient = useQueryClient();
  // Всегда false на первом рендере — совпадает с SSR; иначе гидрация ломается (storage есть только в браузере).
  const [hasToken, setHasToken] = useState(false);

  useLayoutEffect(() => {
    setHasToken(computeHasToken());
  }, []);

  useEffect(() => {
    const sync = () => {
      const cookies = authCookiesMode();
      const next =
        !!getAccessToken() || (cookies && (hasAuthSessionHint() || hasAuthSessionFlag()));
      setHasToken(next);
      if (next) {
        void queryClient.prefetchQuery({
          queryKey: AUTH_ME_QUERY_KEY,
          queryFn: authMeQueryFn,
          retry: false,
        });
      } else {
        queryClient.setQueryData<User | null>(AUTH_ME_QUERY_KEY, null);
      }
    };
    sync();
    if (typeof window !== 'undefined') {
      window.addEventListener('ringoo-auth', sync);
      return () => window.removeEventListener('ringoo-auth', sync);
    }
    return undefined;
  }, [queryClient]);

  const {
    data: user,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: AUTH_ME_QUERY_KEY,
    queryFn: authMeQueryFn,
    enabled: hasToken,
    retry: false,
  });

  const logout = async () => {
    await logoutAuth();
    queryClient.setQueryData<User | null>(AUTH_ME_QUERY_KEY, null);
    queryClient.removeQueries({ queryKey: AUTH_STAFF_ACCESS_QUERY_KEY });
    setHasToken(false);
  };

  const setUser = (u: User | null) => {
    queryClient.setQueryData(AUTH_ME_QUERY_KEY, u);
  };

  return {
    user: user ?? null,
    isLoading,
    isError,
    isAuthenticated: isSuccess && !!user,
    logout,
    setUser,
    hasToken,
  };
}
