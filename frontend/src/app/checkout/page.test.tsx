import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CheckoutPage from './page';

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn().mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }),
  getProductStock: vi.fn().mockResolvedValue({ quantity: 10, available: true }),
}));

vi.mock('@/lib/api/services/addresses.service', () => ({
  getAddresses: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isError: false,
    isAuthenticated: false,
    logout: vi.fn(),
    setUser: vi.fn(),
    hasToken: false,
  }),
  AUTH_ME_QUERY_KEY: ['auth', 'me'],
  AUTH_STAFF_ACCESS_QUERY_KEY: ['auth', 'staff-access'],
  authMeQueryFn: vi.fn(),
}));

vi.mock('@/lib/hooks/useCart', () => ({
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
      total_amount: '1000.00',
      created_at: '',
      updated_at: '',
    },
    isLoading: false,
    isPending: false,
    isError: false,
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('CheckoutPage', () => {
  it('renders checkout steps and cart summary', async () => {
    renderWithClient(<CheckoutPage />);

    expect(await screen.findByText('Оформление заказа')).toBeInTheDocument();
    expect(screen.getAllByText(/Шаг 1/).length).toBeGreaterThan(0);
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
  });
});
