'use client';

import { useCallback, useEffect, useState } from 'react';
import { YandexMetrika } from '@/components/analytics/YandexMetrika';
import { CookieConsentBanner } from '@/components/legal/CookieConsentBanner';
import { postAnalyticsConsent } from '@/lib/api/services/legal.service';
import { readAnalyticsConsent, setAnalyticsConsent } from '@/lib/legal/analytics-consent';

export function LegalAnalyticsProviders() {
  const [consent, setConsent] = useState<boolean | null>(null);

  useEffect(() => {
    setConsent(readAnalyticsConsent());
  }, []);

  const applyChoice = useCallback((accepted: boolean) => {
    setAnalyticsConsent(accepted);
    setConsent(accepted);
    if (accepted) {
      postAnalyticsConsent(true).catch(() => {
        /* согласие сохранено локально; лог на сервере не критичен для UX */
      });
    }
  }, []);

  return (
    <>
      <YandexMetrika enabled={consent === true} />
      {consent === null ? (
        <CookieConsentBanner
          onAccept={() => applyChoice(true)}
          onReject={() => applyChoice(false)}
        />
      ) : null}
    </>
  );
}
