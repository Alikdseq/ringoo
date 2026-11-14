import { describe, expect, it } from 'vitest';

import {
  buildCheckoutAttemptFingerprint,
  createCheckoutIdempotencyKey,
  resolveCheckoutIdempotencyKey,
} from './checkout-idempotency';

describe('checkout idempotency (B8-004)', () => {
  it('keeps the same key while fingerprint is unchanged', () => {
    const fingerprint = buildCheckoutAttemptFingerprint({
      cartId: 'c1',
      paymentType: 'cash',
      storeId: 's1',
      deliveryType: 'pickup',
      phone: '79001112233',
      fullName: 'A',
      itemKeys: ['p1:1'],
      acceptPriceChanges: false,
    });
    const first = resolveCheckoutIdempotencyKey({
      fingerprint,
      lastFingerprint: null,
      currentKey: null,
    });
    const second = resolveCheckoutIdempotencyKey({
      fingerprint,
      lastFingerprint: first.fingerprint,
      currentKey: first.key,
    });
    expect(second.key).toBe(first.key);
  });

  it('issues a new key when cart/payment fingerprint changes', () => {
    const a = buildCheckoutAttemptFingerprint({
      cartId: 'c1',
      paymentType: 'cash',
      storeId: 's1',
      deliveryType: 'pickup',
      phone: '79001112233',
      fullName: 'A',
      itemKeys: ['p1:1'],
      acceptPriceChanges: false,
    });
    const b = buildCheckoutAttemptFingerprint({
      cartId: 'c1',
      paymentType: 'online',
      storeId: 's1',
      deliveryType: 'pickup',
      phone: '79001112233',
      fullName: 'A',
      itemKeys: ['p1:1'],
      acceptPriceChanges: false,
    });
    expect(a).not.toBe(b);
    const first = resolveCheckoutIdempotencyKey({
      fingerprint: a,
      lastFingerprint: null,
      currentKey: null,
    });
    const next = resolveCheckoutIdempotencyKey({
      fingerprint: b,
      lastFingerprint: first.fingerprint,
      currentKey: first.key,
    });
    expect(next.key).not.toBe(first.key);
  });

  it('createCheckoutIdempotencyKey returns non-empty string', () => {
    expect(createCheckoutIdempotencyKey().length).toBeGreaterThan(8);
  });
});
