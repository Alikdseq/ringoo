import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { createElement } from 'react';

const logoutAuth = vi.fn(async () => undefined);

vi.mock('@/lib/api/services/auth.service', () => ({
  getMe: vi.fn(),
  logoutAuth: (...args: unknown[]) => logoutAuth(...args),
}));

vi.mock('@/lib/storage/token-storage', () => ({
  getAccessToken: () => null,
}));

vi.mock('@/lib/auth-mode', () => ({
  authCookiesMode: () => false,
  hasAuthSessionFlag: () => false,
  hasAuthSessionHint: () => false,
}));

import { CART_QUERY_KEY } from '@/lib/hooks/useCart';
import { useAuth } from '@/lib/hooks/useAuth';

describe('useAuth logout cart cache (B8-014)', () => {
  beforeEach(() => {
    logoutAuth.mockClear();
  });

  it('cancels and removes cart queries then invalidates guest cart', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    client.setQueryData(CART_QUERY_KEY, {
      id: 'user-cart',
      items: [{ id: '1' }],
      total_amount: '100',
    });

    const cancelSpy = vi.spyOn(client, 'cancelQueries');
    const removeSpy = vi.spyOn(client, 'removeQueries');
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');

    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client }, children);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.logout();
    });

    expect(logoutAuth).toHaveBeenCalled();
    expect(cancelSpy).toHaveBeenCalledWith({ queryKey: CART_QUERY_KEY });
    expect(removeSpy).toHaveBeenCalledWith({ queryKey: CART_QUERY_KEY });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: CART_QUERY_KEY });
    expect(client.getQueryData(CART_QUERY_KEY)).toBeUndefined();
  });
});
