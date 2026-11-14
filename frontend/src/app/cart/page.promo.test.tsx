import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CartPage from './page';

vi.mock('@/components/ringik/Ringik', () => ({
  Ringik: () => null,
}));

vi.mock('@/lib/hooks/useCart', () => ({
  CART_QUERY_KEY: ['cart'],
  useCart: () => ({
    data: {
      id: 'cart1',
      items: [
        {
          id: 'item1',
          quantity: 1,
          price_at_add: '1000.00',
          item_total: '1000.00',
          created_at: '',
          updated_at: '',
          product: {
            id: 'p1',
            title: 'Товар',
            slug: 't',
            price: '1000.00',
            old_price: null,
            rating: 0,
            reviews_count: 0,
            category: {
              id: 'c1',
              title: 'C',
              slug: 'c',
              parent: null,
              description: null,
            },
          },
          store: null,
        },
      ],
      total_amount: '1000.00',
      created_at: '',
      updated_at: '',
    },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
  useUpdateCartItem: () => ({ mutate: vi.fn(), isPending: false }),
  useRemoveCartItem: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe('CartPage promo UI (B8-011)', () => {
  it('does not offer dead promocode apply control', () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <CartPage />
      </QueryClientProvider>
    );
    expect(screen.queryByPlaceholderText(/промокод/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Применить/i })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Оформить заказ/i })).toBeInTheDocument();
  });
});
