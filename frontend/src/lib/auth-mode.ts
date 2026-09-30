/**
 * Режим авторизации через HttpOnly JWT-куки (бэкенд выставляет куки параллельно JSON).
 * В production по умолчанию true (меньше риска XSS с localStorage).
 * Явно NEXT_PUBLIC_USE_AUTH_COOKIES=0 или false — оставить Bearer + localStorage.
 */
let devCookieWarned = false;

export function authCookiesMode(): boolean {
  if (typeof process === 'undefined') return false;
  const v = process.env.NEXT_PUBLIC_USE_AUTH_COOKIES;
  if (v === '0' || v === 'false') {
    if (
      typeof window !== 'undefined' &&
      process.env.NODE_ENV === 'development' &&
      !devCookieWarned
    ) {
      devCookieWarned = true;
      console.warn(
        '[ringoo] NEXT_PUBLIC_USE_AUTH_COOKIES=false: JWT в localStorage. Для staging используйте =1.'
      );
    }
    return false;
  }
  if (v === '1' || v === 'true') return true;
  return process.env.NODE_ENV === 'production';
}

const AUTH_HINT_KEY = 'ringoo_auth_hint';
const AUTH_REMEMBER_KEY = 'ringoo_auth_remember';

/** После входа в cookie-mode: сессия в tab; при «Запомнить меня» — ещё в localStorage. */
export function setAuthSessionHint(rememberMe = false): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(AUTH_HINT_KEY, '1');
  if (rememberMe) {
    localStorage.setItem(AUTH_REMEMBER_KEY, '1');
  } else {
    localStorage.removeItem(AUTH_REMEMBER_KEY);
  }
}

export function clearAuthSessionHint(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(AUTH_HINT_KEY);
  localStorage.removeItem(AUTH_REMEMBER_KEY);
}

const SESSION_FLAG_COOKIE = 'ringoo_session';

/** Не-HttpOnly флаг: гость не дергает /auth/me и refresh без сессии. */
export function hasAuthSessionFlag(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.split(';').some(part => {
    const [name, value] = part.trim().split('=');
    return name === SESSION_FLAG_COOKIE && value === '1';
  });
}

export function hasAuthSessionHint(): boolean {
  if (typeof window === 'undefined') return false;
  return (
    sessionStorage.getItem(AUTH_HINT_KEY) === '1' ||
    localStorage.getItem(AUTH_REMEMBER_KEY) === '1'
  );
}

export function hasRememberMeHint(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(AUTH_REMEMBER_KEY) === '1';
}
