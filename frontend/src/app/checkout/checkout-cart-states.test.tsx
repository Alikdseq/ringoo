import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';

const useCartMock = vi.fn();

vi.mock('@/lib/hooks/useCart', () => ({
  CART_QUERY_KEY: ['cart'],
  useCart: () => useCartMock(),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthenticated: false, user: null }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn(async () => []),
  getProductStock: vi.fn(async () => ({ results: [] })),
}));

import CheckoutPage from './page';

function renderPage(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('CheckoutPage cart states (B8-012)', () => {
  it('shows error state, not empty cart, when cart query failed', () => {
    useCartMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: { response: { status: 500 } },
      refetch: vi.fn(),
    });
    renderPage(<CheckoutPage />);
    expect(screen.getByText(/Не удалось загрузить корзину для оформления/i)).toBeInTheDocument();
    expect(screen.queryByText(/Корзина пуста/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Повторить/i })).toBeInTheDocument();
  });

  it('shows empty cart when cart loaded with no items', () => {
    useCartMock.mockReturnValue({
      data: { id: 'c', items: [], total_amount: '0.00' },
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    renderPage(<CheckoutPage />);
    expect(screen.getByText(/Корзина пуста/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/Не удалось загрузить корзину для оформления/i)
    ).not.toBeInTheDocument();
  });
});
