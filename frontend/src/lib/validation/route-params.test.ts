import { describe, expect, it } from 'vitest';

import { isOrderIdParam } from './route-params';

describe('isOrderIdParam', () => {
  it('accepts uuid v4', () => {
    expect(isOrderIdParam('550e8400-e29b-41d4-a716-446655440000')).toBe(true);
  });

  it('rejects non-uuid', () => {
    expect(isOrderIdParam('../../../etc/passwd')).toBe(false);
    expect(isOrderIdParam('not-a-uuid')).toBe(false);
    expect(isOrderIdParam('')).toBe(false);
  });
});
