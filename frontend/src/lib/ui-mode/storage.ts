import { UI_MODE_COOKIE_NAME, UI_MODE_STORAGE_KEY, type UiMode } from '@/lib/ui-mode/types';

const COOKIE_MAX_AGE_SEC = 60 * 60 * 24 * 365;

export function isUiMode(v: unknown): v is UiMode {
  return v === 'official' || v === 'svoi';
}

export function readUiModeFromCookie(): UiMode | null {
  if (typeof document === 'undefined') return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${UI_MODE_COOKIE_NAME}=(official|svoi)(?:;|$)`));
  const v = m?.[1];
  return isUiMode(v) ? v : null;
}

export function readUiModeFromLocalStorage(): UiMode | null {
  if (typeof window === 'undefined') return null;
  try {
    const v = localStorage.getItem(UI_MODE_STORAGE_KEY);
    return isUiMode(v) ? v : null;
  } catch {
    return null;
  }
}

/** Приоритет: cookie → localStorage → null */
export function readPersistedUiMode(): UiMode | null {
  return readUiModeFromCookie() ?? readUiModeFromLocalStorage();
}

export function persistUiMode(mode: UiMode): void {
  try {
    localStorage.setItem(UI_MODE_STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
  try {
    document.cookie = `${UI_MODE_COOKIE_NAME}=${mode}; path=/; max-age=${COOKIE_MAX_AGE_SEC}; SameSite=Lax`;
  } catch {
    /* ignore */
  }
}

export function applyUiModeToDocument(mode: UiMode): void {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.uiMode = mode;
  document.body.classList.remove('mode-official', 'mode-svoi');
  document.body.classList.add(mode === 'svoi' ? 'mode-svoi' : 'mode-official');
}
