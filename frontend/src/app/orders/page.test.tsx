import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { User } from '@/types';
import OrdersPage from './page';

const mockReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
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
  getOrders: vi.fn().mockResolvedValue({
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id: 'o1',
        order_number: 'R-1001',
        full_name: 'Иван Иванов',
        phone: '+7 777 123 45 67',
        email: 'test@example.com',
        delivery_type: 'pickup',
        delivery_address: {},
        store: null,
        payment_type: 'cash',
        status: 'new',
        total_amount: '1500.00',
        delivery_cost: '0.00',
        bonus_used: '0.00',
        bonus_earned: '100.00',
        comment: null,
        items: [],
        created_at: '2024-01-01T10:00:00Z',
        updated_at: '2024-01-01T10:00:00Z',
      },
    ],
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('OrdersPage', () => {
  it('renders orders list and breadcrumbs', async () => {
    renderWithClient(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /мои заказы/i })).toBeInTheDocument();
    });

    expect(screen.getByText(/заказ r-1001/i)).toBeInTheDocument();
    expect(screen.getByText('1500.00 ₽')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Профиль' })).toHaveAttribute('href', '/profile');
    expect(screen.getByRole('link', { name: /заказ r-1001/i })).toHaveAttribute(
      'href',
      '/orders/o1'
    );
    expect(
      screen.getByRole('button', { name: /скопировать номер заказа r-1001/i })
    ).toBeInTheDocument();
  });

  it('shows localized status for order', async () => {
    renderWithClient(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText('Новый')).toBeInTheDocument();
    });
  });
});
