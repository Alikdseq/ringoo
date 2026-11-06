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
          quantity: 2,
          price_at_add: '1000.00',
          item_total: '2000.00',
          created_at: '',
          updated_at: '',
          product: {
            id: 'p1',
            title: 'Тестовый товар',
            slug: 'test-product',
            price: '1000.00',
            old_price: null,
            rating: 4.5,
            reviews_count: 10,
            category: {
              id: 'c1',
              title: 'Категория',
              slug: 'cat',
              parent: null,
              description: null,
            },
          },
          store: null,
        },
      ],
      total_amount: '2000.00',
      created_at: '',
      updated_at: '',
    },
    isLoading: false,
    isPending: false,
    isError: false,
    error: null,
    status: 'success',
  }),
  useUpdateCartItem: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useRemoveCartItem: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('CartPage', () => {
  it('renders cart items and total', () => {
    renderWithClient(<CartPage />);

    expect(screen.getByText('Корзина')).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
    expect(screen.getAllByText(/2000\.00/).length).toBeGreaterThan(0);
  });
});
