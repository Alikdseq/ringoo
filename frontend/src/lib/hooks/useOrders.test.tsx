import { describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useOrder, useOrders } from './useOrders';

vi.mock('@/lib/api/services/orders.service', () => ({
  getOrder: vi.fn().mockResolvedValue({
    id: 'o1',
    order_number: 'R-1001',
  }),
  getOrders: vi.fn().mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id: 'o1',
        order_number: 'R-1001',
      },
    ],
  }),
  createOrder: vi.fn(),
}));

function createWrapper() {
  const client = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('useOrder', () => {
  it('returns loading state initially', () => {
    const { result } = renderHook(() => useOrder('o1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe('useOrders', () => {
  it('returns loading state initially', () => {
    const { result } = renderHook(
      () =>
        useOrders({
          status: 'created',
        }),
      {
        wrapper: createWrapper(),
      }
    );

    expect(result.current.isLoading).toBe(true);
  });
});
