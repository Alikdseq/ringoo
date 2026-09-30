import { describe, expect, it, beforeEach } from 'vitest';
import {
  ANALYTICS_CONSENT_COOKIE,
  readAnalyticsConsent,
  setAnalyticsConsent,
} from './analytics-consent';

describe('analytics-consent', () => {
  beforeEach(() => {
    document.cookie = `${ANALYTICS_CONSENT_COOKIE}=; path=/; max-age=0`;
    localStorage.removeItem('ringoo_analytics_consent');
  });

  it('returns null when no choice stored', () => {
    expect(readAnalyticsConsent()).toBeNull();
  });

  it('persists accept choice in cookie and storage', () => {
    setAnalyticsConsent(true);
    expect(readAnalyticsConsent()).toBe(true);
    expect(document.cookie).toContain(`${ANALYTICS_CONSENT_COOKIE}=1`);
  });

  it('persists reject choice', () => {
    setAnalyticsConsent(false);
    expect(readAnalyticsConsent()).toBe(false);
  });
});
