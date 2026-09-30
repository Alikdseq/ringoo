import { apiClient } from '@/lib/api/client';
import { authCookiesMode, clearAuthSessionHint, setAuthSessionHint } from '@/lib/auth-mode';
import { clearAuthTokens, getRefreshToken, setAuthTokens } from '@/lib/storage/token-storage';
import type { User } from '@/types';

function notifyAuthSessionChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event('ringoo-auth'));
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

/** Вход по телефону и паролю. POST /api/v1/auth/token/ (username=phone) */
export async function login(
  phone: string,
  password: string,
  rememberMe = false
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/token/', {
    username: phone,
    password,
  });
  if (authCookiesMode()) {
    setAuthSessionHint(rememberMe);
  } else {
    setAuthTokens(data.access, data.refresh);
  }
  notifyAuthSessionChanged();
  return data;
}

export interface RegisterBody {
  phone: string;
  password: string;
  last_name?: string;
  first_name?: string;
  middle_name?: string;
  consent_personal_data: boolean;
  consent_offer: boolean;
  consent_marketing?: boolean;
}

export interface RegisterResponse {
  detail: string;
  access: string;
  refresh: string;
}

/** Регистрация: телефон, пароль, ФИО. POST /api/v1/auth/register/ */
export async function register(body: RegisterBody): Promise<RegisterResponse> {
  const { data } = await apiClient.post<RegisterResponse>('/auth/register/', body);
  if (authCookiesMode()) {
    setAuthSessionHint();
  } else {
    setAuthTokens(data.access, data.refresh);
  }
  notifyAuthSessionChanged();
  return data;
}

/** Выход: blacklist refresh, сброс кук на сервере и локального состояния. */
export async function logoutAuth(): Promise<void> {
  try {
    const body =
      authCookiesMode() ? {} : { refresh: getRefreshToken() ?? undefined };
    await apiClient.post('/auth/logout/', body);
  } catch {
    /* сеть / уже разлогинен */
  }
  clearAuthTokens();
  clearAuthSessionHint();
  notifyAuthSessionChanged();
}

/** Текущий пользователь. GET /api/v1/auth/me/ (требует авторизации) */
export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me/');
  return data;
}

/** Согласие на маркетинг: PATCH /api/v1/auth/me/ */
export async function updateMarketingOptIn(marketing_opt_in: boolean): Promise<User> {
  const { data } = await apiClient.patch<User>('/auth/me/', { marketing_opt_in });
  return data;
}

/** Экспорт персональных данных (JSON). GET /api/v1/auth/me/export/ */
export async function exportMyData(): Promise<unknown> {
  const { data } = await apiClient.get<unknown>('/auth/me/export/');
  return data;
}

/** Удаление аккаунта и анонимизация. POST /api/v1/auth/delete-account/ */
export async function deleteAccount(): Promise<void> {
  await apiClient.post('/auth/delete-account/', { confirm: 'DELETE_MY_ACCOUNT' });
}

/**
 * Доступ к админ-панели (is_staff). GET /api/v1/auth/staff-access/
 * — 200 только для сотрудников; не смешивать с публичным /me/.
 */
export async function checkStaffAccess(): Promise<boolean> {
  try {
    await apiClient.get<{ staff?: boolean }>('/auth/staff-access/');
    return true;
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status;
    if (status === 403 || status === 401) return false;
    throw e;
  }
}
