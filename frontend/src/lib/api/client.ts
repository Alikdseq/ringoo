import axios, { type AxiosError, type AxiosRequestConfig } from 'axios';
import { authCookiesMode, hasAuthSessionFlag, hasAuthSessionHint } from '@/lib/auth-mode';
import { getCsrfTokenFromCookie } from '@/lib/csrf';
import {
  clearAuthTokens,
  getAccessToken,
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

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const isNgrokApi =
  typeof API_BASE_URL === 'string' && API_BASE_URL.includes('ngrok-free.dev');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // обязательно для сессии гостя (корзина по session_key)
  timeout: 10000,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(isNgrokApi ? { 'ngrok-skip-browser-warning': '1' } : {}),
  },
});

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

// --- Interceptors: добавление токенов, refresh, retry ---

apiClient.interceptors.request.use(config => {
  if (authCookiesMode()) {
    config.headers = config.headers ?? {};
    config.headers['X-Auth-Cookies'] = '1';
    const method = (config.method ?? 'get').toLowerCase();
    if (UNSAFE_METHODS.has(method)) {
      const csrf = getCsrfTokenFromCookie();
      if (csrf) {
        config.headers['X-CSRFToken'] = csrf;
      }
    }
    return config;
  }
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

/**
 * Возвращает новый access для Bearer, либо "" если обновление только через HttpOnly-куки.
 */
async function refreshAccessToken(): Promise<string | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const instance = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
    timeout: 10000,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Auth-Cookies': '1',
      ...(isNgrokApi ? { 'ngrok-skip-browser-warning': '1' } : {}),
    },
  });

  if (authCookiesMode()) {
    if (!getRefreshToken() && !hasAuthSessionHint() && !hasAuthSessionFlag()) {
      return null;
    }
    isRefreshing = true;
    refreshPromise = instance
      .post<{ access?: string; refresh?: string }>('/auth/token/refresh/', {})
      .then(() => '')
      .catch(() => {
        clearAuthTokens();
        return null;
      })
      .finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    return refreshPromise;
  }

  const refresh = getRefreshToken();
  if (!refresh) return null;

  isRefreshing = true;
  refreshPromise = instance
    .post<{ access: string; refresh?: string }>('/auth/token/refresh/', { refresh })
    .then(response => {
      const newAccess = response.data.access;
      const newRefresh = response.data.refresh ?? refresh;
      setAuthTokens(newAccess, newRefresh);
      return newAccess;
    })
    .catch(() => {
      clearAuthTokens();
      return null;
    })
    .finally(() => {
      isRefreshing = false;
      refreshPromise = null;
    });

  return refreshPromise;
}

type RetryConfig = AxiosRequestConfig & {
  _retry?: boolean;
  /** Повтор GET без Bearer после неудачного refresh (протухший JWT в localStorage + публичный эндпоинт). */
  _guestRetry?: boolean;
};

apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryConfig | undefined;
    const status = error.response?.status;

    if (status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;
      const newAccess = await refreshAccessToken();
      if (newAccess !== null) {
        originalRequest.headers = {
          ...(originalRequest.headers ?? {}),
        };
        if (newAccess) {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        } else {
          delete originalRequest.headers.Authorization;
        }
        return apiClient(originalRequest);
      }
      const method = (originalRequest.method ?? 'get').toLowerCase();
      if (method === 'get' && !originalRequest._guestRetry) {
        originalRequest._guestRetry = true;
        originalRequest.headers = { ...(originalRequest.headers ?? {}) };
        delete originalRequest.headers.Authorization;
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);
