import { describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCart } from './useCart';

vi.mock('@/lib/api/services/cart.service', () => ({
  getCart: vi.fn().mockResolvedValue({
    id: 'cart1',
    items: [],
    total_amount: '0.00',
    created_at: '',
    updated_at: '',
  }),
}));

function createWrapper() {
  const client = new QueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('useCart', () => {
  it('returns initial loading state', () => {
    const { result } = renderHook(() => useCart(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});
