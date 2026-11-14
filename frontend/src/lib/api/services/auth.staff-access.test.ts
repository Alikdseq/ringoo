import { describe, expect, it, vi, beforeEach } from 'vitest';

const get = vi.fn();

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => get(...args),
  },
}));

import { checkStaffAccess, fetchStaffAccess } from './auth.service';

describe('fetchStaffAccess (Fix F)', () => {
  beforeEach(() => {
    get.mockReset();
  });

  it('returns normalized staff payload on 200', async () => {
    get.mockResolvedValue({
      data: { staff: true, is_superuser: false, groups: ['ringoo_orders'] },
    });
    await expect(fetchStaffAccess()).resolves.toEqual({
      staff: true,
      is_superuser: false,
      groups: ['ringoo_orders'],
    });
  });

  it('throws on 403 instead of returning null', async () => {
    get.mockRejectedValue({ response: { status: 403 } });
    await expect(fetchStaffAccess()).rejects.toMatchObject({
      response: { status: 403 },
    });
  });

  it('checkStaffAccess returns false on 403', async () => {
    get.mockRejectedValue({ response: { status: 403 } });
    await expect(checkStaffAccess()).resolves.toBe(false);
  });
});
