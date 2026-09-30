/** Cookie и localStorage для согласия на аналитику (Яндекс.Метрика). */

export const ANALYTICS_CONSENT_COOKIE = 'ringoo_analytics_consent';
export const ANALYTICS_CONSENT_STORAGE_KEY = 'ringoo_analytics_consent';
const CONSENT_MAX_AGE_SEC = 365 * 24 * 60 * 60;

export type AnalyticsConsentValue = '1' | '0';

function readCookie(): AnalyticsConsentValue | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${ANALYTICS_CONSENT_COOKIE}=(0|1)(?:;|$)`)
  );
  return match ? (match[1] as AnalyticsConsentValue) : null;
}

/** null — выбор ещё не сделан */
export function readAnalyticsConsent(): boolean | null {
  if (typeof window === 'undefined') return null;
  const fromCookie = readCookie();
  if (fromCookie === '1') return true;
  if (fromCookie === '0') return false;
  try {
    const stored = localStorage.getItem(ANALYTICS_CONSENT_STORAGE_KEY);
    if (stored === '1') return true;
    if (stored === '0') return false;
  } catch {
    /* ignore */
  }
  return null;
}

export function setAnalyticsConsent(accepted: boolean): void {
  const value: AnalyticsConsentValue = accepted ? '1' : '0';
  if (typeof document !== 'undefined') {
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${ANALYTICS_CONSENT_COOKIE}=${value}; path=/; max-age=${CONSENT_MAX_AGE_SEC}; SameSite=Lax${secure}`;
  }
  try {
    localStorage.setItem(ANALYTICS_CONSENT_STORAGE_KEY, value);
  } catch {
    /* ignore */
  }
}
