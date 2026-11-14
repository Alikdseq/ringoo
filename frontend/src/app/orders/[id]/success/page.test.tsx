import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Order } from '@/types';
import OrderSuccessPage from './page';

const ORDER_ID = '550e8400-e29b-41d4-a716-446655440000';

const { getOrder, takePayAuth, useAuthMock, routerReplace } = vi.hoisted(() => ({
  getOrder: vi.fn(),
  takePayAuth: vi.fn(),
  useAuthMock: vi.fn(),
  routerReplace: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: ORDER_ID }),
  useRouter: () => ({ replace: routerReplace, push: vi.fn() }),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('@/lib/api/services/orders.service', () => ({
  getOrder: (...args: unknown[]) => getOrder(...args),
}));

vi.mock('@/lib/api/services/payments.service', () => ({
  takePayAuth: (...args: unknown[]) => takePayAuth(...args),
}));

const baseOrder = {
  id: ORDER_ID,
  order_number: 'R-1001',
  full_name: 'Иван Иванов',
  phone: '+7 777 123 45 67',
  email: 'test@example.com',
  delivery_type: 'pickup',
  delivery_address: {},
  store: null,
  payment_type: 'cash',
  status: 'new',
  total_amount: '1000.00',
  delivery_cost: '0.00',
  bonus_used: '0.00',
  bonus_earned: '0.00',
  comment: null,
  items: [
    {
      id: 'oi1',
      product_title: 'Тестовый товар',
      quantity: 1,
      price: '1000.00',
      item_total: '1000.00',
    },
  ],
  created_at: '',
  updated_at: '',
} satisfies Order;

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrderSuccessPage (/orders/[id]/success)', () => {
  beforeEach(() => {
    getOrder.mockReset();
    takePayAuth.mockReset();
    routerReplace.mockReset();
    useAuthMock.mockReset();
  });

  it('loads order via getOrder when authenticated (useParams id)', async () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    getOrder.mockResolvedValue(baseOrder);

    renderWithClient(<OrderSuccessPage />);

    expect(await screen.findByText('Заказ оформлен')).toBeInTheDocument();
    expect(screen.getByText('R-1001')).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
    expect(getOrder).toHaveBeenCalledWith(ORDER_ID);
  });

  it('does not call getOrder for guest; redirects to public success when stash exists', async () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });
    takePayAuth.mockReturnValue({
      phone: '79001234567',
      order_number: 'R-1001',
      guest_token: 'tok',
    });

    renderWithClient(<OrderSuccessPage />);

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith('/orders/success?order_number=R-1001');
    });
    expect(getOrder).not.toHaveBeenCalled();
  });

  it('does not call getOrder for guest without stash', async () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });
    takePayAuth.mockReturnValue(null);

    renderWithClient(<OrderSuccessPage />);

    expect(
      await screen.findByText(/Для просмотра статуса укажите номер и телефон/i)
    ).toBeInTheDocument();
    expect(getOrder).not.toHaveBeenCalled();
  });
});
