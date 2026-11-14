import { describe, expect, it } from 'vitest';

import { resolveCashCheckoutSuccessPath } from './checkout-success-path';

describe('resolveCashCheckoutSuccessPath', () => {
  it('sends guest to public success with order_number (no auth-only detail URL)', () => {
    expect(
      resolveCashCheckoutSuccessPath({
        isAuthenticated: false,
        orderId: '550e8400-e29b-41d4-a716-446655440000',
        orderNumber: 'R-1001',
      })
    ).toBe('/orders/success?order_number=R-1001');
  });

  it('encodes order_number for query string', () => {
    expect(
      resolveCashCheckoutSuccessPath({
        isAuthenticated: false,
        orderId: 'o1',
        orderNumber: 'R 1001/A',
      })
    ).toBe('/orders/success?order_number=R%201001%2FA');
  });

  it('sends authenticated buyer to /orders/{id}/success', () => {
    expect(
      resolveCashCheckoutSuccessPath({
        isAuthenticated: true,
        orderId: '550e8400-e29b-41d4-a716-446655440000',
        orderNumber: 'R-1001',
      })
    ).toBe('/orders/550e8400-e29b-41d4-a716-446655440000/success');
  });

  it('guest without order_number still lands on public success (no getOrder)', () => {
    expect(
      resolveCashCheckoutSuccessPath({
        isAuthenticated: false,
        orderId: 'o1',
        orderNumber: '',
      })
    ).toBe('/orders/success');
  });
});
