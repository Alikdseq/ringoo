/**
 * Централизованный JWT refresh (single-flight).
 * Отдельный модуль от apiClient, чтобы не крутить refresh через собственные interceptors.
 */
import axios from 'axios';
import {
  authCookiesMode,
  clearAuthSessionHint,
  hasAuthSessionFlag,
  hasAuthSessionHint,
  notifyAuthSessionChanged,
} from '@/lib/auth-mode';
import {
  clearAuthTokens,
  getRefreshToken,
  setAuthTokens,
} from '@/lib/storage/token-storage';

function resolveApiBaseUrl(): string {
  const explicit =
    process.env.NEXT_PUBLIC_API_V1_URL ??
    (process.env.NEXT_PUBLIC_API_URL
      ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '')}/api/v1`
      : '');
  const pointsAtLocalMachine = /localhost|127\.0\.0\.1|0\.0\.0\.0|host\.docker\.internal/i.test(
    explicit
  );
  const onVercel = process.env.VERCEL === '1';
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const browserIsLocal = host === 'localhost' || host === '127.0.0.1';
    if (!browserIsLocal && (onVercel || !explicit || pointsAtLocalMachine)) {
      return '/api/v1';
    }
  } else if (onVercel && process.env.VERCEL_URL && (!explicit || pointsAtLocalMachine)) {
    return `https://${process.env.VERCEL_URL.replace(/\/+$/, '')}/api/v1`;
  }
  if (explicit) return explicit.replace(/\/+$/, '');
  return 'http://localhost:8000/api/v1';
}

const API_BASE_URL = resolveApiBaseUrl();
const isNgrokApi = typeof API_BASE_URL === 'string' && API_BASE_URL.includes('ngrok-free.dev');

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;
let refreshEpoch = 0;

/** Сброс очереди refresh — logout, чтобы отложенный refresh не восстановил сессию. */
export function invalidatePendingAuthRefresh(): void {
  refreshEpoch += 1;
  isRefreshing = false;
  refreshPromise = null;
}

function clearLocalAuthSession(): void {
  clearAuthTokens();
  clearAuthSessionHint();
  notifyAuthSessionChanged();
}

/**
 * Новый access для Bearer, либо "" при cookie-refresh.
 * null — неудача / сессия сброшена.
 *
 * B8-002: X-Auth-Cookies только в cookie-режиме.
 * B8-006: при ошибке чистим tokens + session hint.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const epoch = refreshEpoch;
  const cookies = authCookiesMode();

  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(isNgrokApi ? { 'ngrok-skip-browser-warning': '1' } : {}),
  };
  if (cookies) {
    headers['X-Auth-Cookies'] = '1';
  }

  const instance = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
    timeout: 10000,
    headers,
  });

  if (cookies) {
    if (!getRefreshToken() && !hasAuthSessionHint() && !hasAuthSessionFlag()) {
      return null;
    }
    isRefreshing = true;
    refreshPromise = instance
      .post<{ access?: string; refresh?: string }>('/auth/token/refresh/', {})
      .then(() => {
        if (epoch !== refreshEpoch) return null;
        return '';
      })
      .catch(() => {
        if (epoch === refreshEpoch) {
          clearLocalAuthSession();
        }
        return null;
      })
      .finally(() => {
        if (epoch === refreshEpoch) {
          isRefreshing = false;
          refreshPromise = null;
        }
      });
    return refreshPromise;
  }

  const refresh = getRefreshToken();
  if (!refresh) return null;

  isRefreshing = true;
  refreshPromise = instance
    .post<{ access?: string; refresh?: string }>('/auth/token/refresh/', { refresh })
    .then(response => {
      if (epoch !== refreshEpoch) return null;
      const newAccess = response.data.access;
      if (!newAccess) {
        clearLocalAuthSession();
        return null;
      }
      const newRefresh = response.data.refresh ?? refresh;
      setAuthTokens(newAccess, newRefresh);
      return newAccess;
    })
    .catch(() => {
      if (epoch === refreshEpoch) {
        clearLocalAuthSession();
      }
      return null;
    })
    .finally(() => {
      if (epoch === refreshEpoch) {
        isRefreshing = false;
        refreshPromise = null;
      }
    });

  return refreshPromise;
}
