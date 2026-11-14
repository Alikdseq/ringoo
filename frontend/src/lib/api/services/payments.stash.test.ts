import { beforeEach, describe, expect, it } from 'vitest';

import {
  peekGuestTokenByOrderNumber,
  stashGuestTokenByOrderNumber,
  stashPayAuth,
  takePayAuth,
} from './payments.service';

describe('guest pay stash (B8-005)', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('stashPayAuth survives takePayAuth (reload-safe, no consume)', () => {
    stashPayAuth('ord-1', {
      phone: '79001112233',
      order_number: 'R-1',
      guest_token: 'tok-abc',
    });
    expect(takePayAuth('ord-1')).toEqual({
      phone: '79001112233',
      order_number: 'R-1',
      guest_token: 'tok-abc',
    });
    expect(takePayAuth('ord-1')?.guest_token).toBe('tok-abc');
    expect(peekGuestTokenByOrderNumber('R-1')).toBe('tok-abc');
  });

  it('merges guest token from order_number stash when pay_auth lacks token', () => {
    sessionStorage.setItem(
      'ringoo_pay_auth:ord-2',
      JSON.stringify({ phone: '79001112233', order_number: 'R-2' })
    );
    stashGuestTokenByOrderNumber('R-2', 'tok-from-number');
    expect(takePayAuth('ord-2')?.guest_token).toBe('tok-from-number');
  });

  it('does not put token into empty takePayAuth for unknown order', () => {
    expect(takePayAuth('missing')).toBeNull();
  });
});
