import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';

const getOrder = vi.fn();
const useAuthMock = vi.fn();

const ORDER_ID = '11111111-1111-4111-a111-111111111111';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: ORDER_ID }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('@/lib/api/services/orders.service', () => ({
  getOrder: (...args: unknown[]) => getOrder(...args),
  cancelOrder: vi.fn(),
  reorderOrder: vi.fn(),
}));

vi.mock('@/lib/api/services/payments.service', () => ({
  initiateOrderPayment: vi.fn(),
  isOnlinePaymentUiEnabled: () => false,
  stashPayAuth: vi.fn(),
}));

import OrderDetailPage from './page';

function renderPage(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrderDetailPage states (B8-013)', () => {
  beforeEach(() => {
    getOrder.mockReset();
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      hasToken: true,
    });
  });

  it('shows not-found for 404 without leaking order data', async () => {
    getOrder.mockRejectedValue({ response: { status: 404 } });
    renderPage(<OrderDetailPage />);
    expect(await screen.findByText('Заказ не найден')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /К списку заказов/i })).toBeInTheDocument();
  });

  it('shows not-found phrasing for 403 (no IDOR leak)', async () => {
    getOrder.mockRejectedValue({ response: { status: 403 } });
    renderPage(<OrderDetailPage />);
    expect(await screen.findByText('Заказ не найден')).toBeInTheDocument();
  });

  it('wires support CTA to confirmed legal email when order loads', async () => {
    getOrder.mockResolvedValue({
      id: ORDER_ID,
      order_number: 'R-100',
      status: 'new',
      payment_type: 'cash',
      payment_status: 'pending',
      delivery_type: 'pickup',
      total_amount: '1000.00',
      delivery_cost: '0.00',
      phone: '79001112233',
      full_name: 'Test',
      items: [],
      created_at: '2026-01-01T00:00:00Z',
      can_pay: false,
      can_cancel: false,
    });
    renderPage(<OrderDetailPage />);
    const link = await screen.findByRole('link', { name: /Написать на/i });
    expect(link.getAttribute('href')).toMatch(/^mailto:/);
    expect(link.getAttribute('href')).toContain('R-100');
  });
});
