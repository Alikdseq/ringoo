import { describe, expect, it, vi, afterEach } from 'vitest';

describe('isOnlinePaymentUiEnabled', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('is false by default / when unset', async () => {
    vi.stubEnv('NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED', '');
    const { isOnlinePaymentUiEnabled } = await import('./payments.service');
    expect(isOnlinePaymentUiEnabled()).toBe(false);
  });

  it('is true only for explicit 1/true/yes', async () => {
    vi.stubEnv('NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED', '1');
    const { isOnlinePaymentUiEnabled } = await import('./payments.service');
    expect(isOnlinePaymentUiEnabled()).toBe(true);
  });

  it('rejects arbitrary truthy strings', async () => {
    vi.stubEnv('NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED', 'on');
    const { isOnlinePaymentUiEnabled } = await import('./payments.service');
    expect(isOnlinePaymentUiEnabled()).toBe(false);
  });
});
