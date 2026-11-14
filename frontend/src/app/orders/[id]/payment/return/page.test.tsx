import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';

const invalidateQueries = vi.fn();
const getOrderPaymentStatus = vi.fn();
const takePayAuth = vi.fn();
const useAuthMock = vi.fn();

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'order-1' }),
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock('@/lib/api/services/payments.service', () => ({
  getOrderPaymentStatus: (...args: unknown[]) => getOrderPaymentStatus(...args),
  takePayAuth: (...args: unknown[]) => takePayAuth(...args),
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>(
    '@tanstack/react-query'
  );
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries,
    }),
  };
});

import PaymentReturnPage from './page';

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('PaymentReturnPage (B8-005)', () => {
  beforeEach(() => {
    invalidateQueries.mockClear();
    getOrderPaymentStatus.mockReset();
    takePayAuth.mockReset();
    useAuthMock.mockReset();
    useAuthMock.mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
      hasToken: false,
    });
  });

  it('does not call payment API for guest without stash (no 403 spam)', async () => {
    takePayAuth.mockReturnValue(null);
    renderWithClient(<PaymentReturnPage />);
    expect(await screen.findByText(/Нужен доступ к заказу/i)).toBeInTheDocument();
    expect(getOrderPaymentStatus).not.toHaveBeenCalled();
  });

  it('does not invalidate cart while payment is pending', async () => {
    takePayAuth.mockReturnValue({
      phone: '79001112233',
      order_number: 'R-1',
      guest_token: 'tok',
    });
    getOrderPaymentStatus.mockResolvedValue({
      payment: {
        status: 'pending',
        order_number: 'R-1',
        amount: '1000.00',
      },
    });

    renderWithClient(<PaymentReturnPage />);

    expect(
      await screen.findByText(/Ожидаем подтверждение оплаты|Проверяем оплату/)
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(getOrderPaymentStatus).toHaveBeenCalled();
    });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });

  it('invalidates cart only after backend confirms paid', async () => {
    takePayAuth.mockReturnValue({
      phone: '79001112233',
      order_number: 'R-1',
      guest_token: 'tok',
    });
    getOrderPaymentStatus.mockResolvedValue({
      payment: {
        status: 'paid',
        order_number: 'R-1',
        amount: '1000.00',
      },
    });

    renderWithClient(<PaymentReturnPage />);

    expect(await screen.findByText('Оплата прошла успешно')).toBeInTheDocument();
    await waitFor(() => {
      expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['cart'] });
    });
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['orders'] });
  });

  it('authenticated user can poll without guest stash', async () => {
    useAuthMock.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      hasToken: true,
    });
    takePayAuth.mockReturnValue(null);
    getOrderPaymentStatus.mockResolvedValue({
      payment: {
        status: 'paid',
        order_number: 'R-1',
        amount: '1000.00',
      },
    });

    renderWithClient(<PaymentReturnPage />);
    expect(await screen.findByText('Оплата прошла успешно')).toBeInTheDocument();
    expect(getOrderPaymentStatus).toHaveBeenCalled();
  });
});
