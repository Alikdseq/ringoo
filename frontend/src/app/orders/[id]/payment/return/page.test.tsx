import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';

const invalidateQueries = vi.fn();
const getOrderPaymentStatus = vi.fn();

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'order-1' }),
}));

vi.mock('@/lib/api/services/payments.service', () => ({
  getOrderPaymentStatus: (...args: unknown[]) => getOrderPaymentStatus(...args),
  takePayAuth: () => null,
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

describe('PaymentReturnPage cart invalidation', () => {
  beforeEach(() => {
    invalidateQueries.mockClear();
    getOrderPaymentStatus.mockReset();
  });

  it('does not invalidate cart while payment is pending', async () => {
    getOrderPaymentStatus.mockResolvedValue({
      payment: {
        status: 'pending',
        order_number: 'R-1',
        amount: '1000.00',
      },
    });

    renderWithClient(<PaymentReturnPage />);

    expect(await screen.findByText(/Ожидаем подтверждение оплаты|Проверяем оплату/)).toBeInTheDocument();
    await waitFor(() => {
      expect(getOrderPaymentStatus).toHaveBeenCalled();
    });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });

  it('invalidates cart only after backend confirms paid', async () => {
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

  it('does not invalidate cart on failed payment', async () => {
    getOrderPaymentStatus.mockResolvedValue({
      payment: {
        status: 'failed',
        order_number: 'R-1',
        amount: '1000.00',
      },
    });

    renderWithClient(<PaymentReturnPage />);

    expect(await screen.findByText('Оплата не подтверждена')).toBeInTheDocument();
    await waitFor(() => {
      expect(getOrderPaymentStatus).toHaveBeenCalled();
    });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
