import { apiClient } from '@/lib/api/client';
import type { StaffAccessInfo } from '@/lib/admin/nav-access';
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
  admin_mfa_required?: boolean;
  mfa_enrolled?: boolean;
  admin_mfa?: boolean;
}

export interface AdminMfaStatus {
  otp_enabled: boolean;
  staff: boolean;
  mfa_required: boolean;
  mfa_enrolled: boolean;
  admin_mfa_verified: boolean;
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
    const body = authCookiesMode() ? {} : { refresh: getRefreshToken() ?? undefined };
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

/** Сырой JSON staff-access до нормализации (поля могут отсутствовать у старых клиентов). */
type StaffAccessApiPayload = {
  staff?: boolean;
  is_superuser?: boolean;
  groups?: unknown;
};

/** Нормализованный контракт = StaffAccessInfo (backend всегда отдаёт все три поля). */
export type StaffAccessResponse = StaffAccessInfo;

/**
 * Доступ к админ-панели (is_staff + группы). GET /api/v1/auth/staff-access/
 * — 200 только для сотрудников; не смешивать с публичным /me/.
 * Ответ нормализуется к StaffAccessInfo: staff, is_superuser, groups[].
 */
export async function fetchStaffAccess(): Promise<StaffAccessInfo | null> {
  try {
    const { data } = await apiClient.get<StaffAccessApiPayload>('/auth/staff-access/');
    const groupsRaw = data?.groups;
    const groups = Array.isArray(groupsRaw)
      ? groupsRaw.filter((g): g is string => typeof g === 'string')
      : [];
    const normalized: StaffAccessInfo = {
      staff: Boolean(data?.staff),
      is_superuser: Boolean(data?.is_superuser),
      groups,
    };
    return normalized;
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status;
    if (status === 403 || status === 401) return null;
    throw e;
  }
}

/** @deprecated используйте fetchStaffAccess для групп; оставлен для boolean-гейтов. */
export async function checkStaffAccess(): Promise<boolean> {
  const access = await fetchStaffAccess();
  return Boolean(access?.staff);
}

/** GET /api/v1/auth/mfa/status/ */
export async function getAdminMfaStatus(): Promise<AdminMfaStatus> {
  const { data } = await apiClient.get<AdminMfaStatus>('/auth/mfa/status/');
  return data;
}

/** POST /api/v1/auth/mfa/verify/ — выдаёт JWT с claim admin_mfa. */
export async function verifyAdminMfa(totp: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/mfa/verify/', { totp });
  if (!authCookiesMode() && data.access && data.refresh) {
    setAuthTokens(data.access, data.refresh);
  }
  notifyAuthSessionChanged();
  return data;
}

/** SEC-009: запрос письма восстановления. Ответ одинаков для любого email. */
export async function requestPasswordReset(email: string): Promise<{ detail: string }> {
  const { data } = await apiClient.post<{ detail: string }>('/auth/password-reset/', {
    email: email.trim(),
  });
  return data;
}

/** SEC-009: установка нового пароля по uid+token из письма. */
export async function confirmPasswordReset(params: {
  uid: string;
  token: string;
  new_password: string;
}): Promise<{ detail: string }> {
  const { data } = await apiClient.post<{ detail: string }>(
    '/auth/password-reset/confirm/',
    params
  );
  return data;
}
