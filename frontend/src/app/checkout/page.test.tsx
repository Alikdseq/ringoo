import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CheckoutPage from './page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn().mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }),
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
  it('renders checkout steps and cart summary', () => {
    renderWithClient(<CheckoutPage />);

    expect(screen.getByText('Оформление заказа')).toBeInTheDocument();
    expect(screen.getByText('Шаг 1. Корзина')).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
  });
});
