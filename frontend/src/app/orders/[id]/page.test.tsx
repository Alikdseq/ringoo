import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Order, User } from '@/types';
import OrderDetailPage from './page';

const { ORDER_ID, getOrder, initiateOrderPayment } = vi.hoisted(() => ({
  ORDER_ID: '11111111-1111-4111-8111-111111111111',
  getOrder: vi.fn(),
  initiateOrderPayment: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ id: ORDER_ID }),
  usePathname: () => `/orders/${ORDER_ID}`,
  useSearchParams: () => new URLSearchParams(),
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
  getOrder: (...args: unknown[]) => getOrder(...args),
  reorderOrder: vi.fn(),
}));

vi.mock('@/lib/api/services/payments.service', () => ({
  initiateOrderPayment: (...args: unknown[]) => initiateOrderPayment(...args),
  isOnlinePaymentUiEnabled: () => true,
  stashPayAuth: vi.fn(),
}));

vi.mock('@/lib/clipboard', () => ({
  copyTextToClipboard: vi.fn().mockResolvedValue(true),
}));

function baseOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: ORDER_ID,
    order_number: 'R-1001',
    full_name: 'Иван Иванов',
    phone: '+7 777 123 45 67',
    email: 'test@example.com',
    delivery_type: 'pickup',
    delivery_address: {},
    store: null,
    payment_type: 'online',
    status: 'new',
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
    can_pay: true,
    payment_status: 'pending',
    ...overrides,
  };
}

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrderDetailPage pay button', () => {
  beforeEach(() => {
    getOrder.mockReset();
    initiateOrderPayment.mockReset();
    // jsdom location.assign
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...window.location, assign: vi.fn() },
    });
  });

  it('renders order details', async () => {
    getOrder.mockResolvedValue(baseOrder({ payment_type: 'cash', can_pay: false, status: 'new' }));
    renderWithClient(<OrderDetailPage />);

    expect(await screen.findByText(/Заказ №?\s*R-1001/i)).toBeInTheDocument();
    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Оплатить' })).not.toBeInTheDocument();
  });

  it('shows Pay button when backend can_pay=true', async () => {
    getOrder.mockResolvedValue(baseOrder({ can_pay: true, status: 'new' }));
    renderWithClient(<OrderDetailPage />);
    expect(await screen.findByRole('button', { name: 'Оплатить' })).toBeInTheDocument();
  });

  it('hides Pay button for paid order', async () => {
    getOrder.mockResolvedValue(
      baseOrder({ can_pay: false, status: 'confirmed', payment_status: 'paid' })
    );
    renderWithClient(<OrderDetailPage />);
    await screen.findByText(/Заказ №?\s*R-1001/i);
    expect(screen.queryByRole('button', { name: 'Оплатить' })).not.toBeInTheDocument();
  });

  it('hides Pay button for cancelled order', async () => {
    getOrder.mockResolvedValue(
      baseOrder({ can_pay: false, status: 'cancelled', payment_status: 'failed' })
    );
    renderWithClient(<OrderDetailPage />);
    await screen.findByText(/Заказ №?\s*R-1001/i);
    expect(screen.queryByRole('button', { name: 'Оплатить' })).not.toBeInTheDocument();
  });

  it('redirects to confirmation_url on pay click', async () => {
    getOrder.mockResolvedValue(baseOrder({ can_pay: true }));
    initiateOrderPayment.mockResolvedValue({
      payment: { id: 'pay1', status: 'pending' },
      form_url: 'https://yookassa.example/pay',
      confirmation_url: 'https://yookassa.example/pay',
      reused: true,
    });
    const user = userEvent.setup();
    renderWithClient(<OrderDetailPage />);
    const btn = await screen.findByRole('button', { name: 'Оплатить' });
    await user.click(btn);
    await waitFor(() => {
      expect(initiateOrderPayment).toHaveBeenCalled();
      expect(window.location.assign).toHaveBeenCalledWith('https://yookassa.example/pay');
    });
  });
});
