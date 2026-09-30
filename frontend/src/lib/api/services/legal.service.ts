import { apiClient } from '@/lib/api/client';

/** POST /api/v1/legal/analytics-consent/ — лог согласия на cookie аналитики */
export async function postAnalyticsConsent(consent: boolean): Promise<void> {
  await apiClient.post('/legal/analytics-consent/', { consent });
}
