import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Order, User } from '@/types';
import OrderDetailPage from './page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ id: 'o1' }),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1' } as User,
    isLoading: false,
    isError: false,
    isAuthenticated: true,
    logout: vi.fn(),
    setUser: vi.fn(),
    hasToken: true,
  }),
}));

vi.mock('@/lib/api/services/orders.service', () => ({
  getOrder: vi.fn().mockResolvedValue({
    id: 'o1',
    order_number: 'R-1001',
    full_name: 'Иван Иванов',
    phone: '+7 777 123 45 67',
    email: 'test@example.com',
    delivery_type: 'pickup',
    delivery_address: {},
    store: null,
    payment_type: 'cash',
    status: 'created',
    total_amount: '1500.00',
    delivery_cost: '0.00',
    bonus_used: '0.00',
    bonus_earned: '100.00',
    comment: 'Позвонить перед доставкой',
    items: [
      {
        id: 'oi1',
        product_title: 'Тестовый товар',
        quantity: 1,
        price: '1500.00',
        item_total: '1500.00',
      },
    ],
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  } satisfies Order),
  reorderOrder: vi.fn(),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrderDetailPage', () => {
  it('renders order details', async () => {
    renderWithClient(<OrderDetailPage />);

    expect(await screen.findByText('Заказ №R-1001')).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
    expect(screen.getByText(/Позвонить перед доставкой/)).toBeInTheDocument();
    expect(screen.getAllByText('1500.00 ₽').length).toBeGreaterThan(0);
  });
});
