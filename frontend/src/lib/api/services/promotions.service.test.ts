import { describe, expect, it, vi, beforeEach } from 'vitest';
import { getPromotions } from './promotions.service';

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

import { apiClient } from '@/lib/api/client';

describe('getPromotions', () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReset();
  });

  it('returns results from paginated API response', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'p1',
            title: 'Test promo',
            discount_type: 'percent',
            discount_value: '10',
            start_date: '2026-01-01T00:00:00Z',
            end_date: '2027-01-01T00:00:00Z',
            category_slugs: [],
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
      },
    });

    const list = await getPromotions();
    expect(list).toHaveLength(1);
    expect(list[0]?.title).toBe('Test promo');
  });

  it('returns plain array when API is not paginated', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ id: 'p2', title: 'Legacy' }],
    });

    const list = await getPromotions();
    expect(list).toHaveLength(1);
    expect(list[0]?.title).toBe('Legacy');
  });
});
