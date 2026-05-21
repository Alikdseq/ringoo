import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProfilePage from './page';

const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

vi.mock('@/lib/api/services/auth.service', () => ({
  getMe: vi.fn(),
  logoutAuth: vi.fn().mockResolvedValue(undefined),
  updateMarketingOptIn: vi.fn(),
  exportMyData: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock('@/lib/api/services/addresses.service', () => ({
  getAddresses: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api/services/wishlist.service', () => ({
  getWishlist: vi.fn().mockResolvedValue([]),
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
        status: 'created',
        total_amount: '1500.00',
        has_rating: false,
      },
    ],
  }),
  getRatingsSummary: vi.fn().mockResolvedValue({
    average: 5,
    count: 1,
    recent: [],
  }),
}));

import { getMe, logoutAuth, updateMarketingOptIn } from '@/lib/api/services/auth.service';

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('ProfilePage', () => {
  beforeEach(() => {
    window.localStorage.setItem('ringoo_access_token', 'test-access-token');
    vi.mocked(getMe).mockResolvedValue({
      id: 'u1',
      phone: '+7 777 123 45 67',
      email: 'user@example.com',
      is_phone_verified: true,
      is_email_verified: false,
      created_at: '',
      updated_at: '',
      privacy_policy_accepted_at: '2025-06-01T12:00:00Z',
      marketing_opt_in: false,
      marketing_opt_in_at: null,
    });
    vi.mocked(updateMarketingOptIn).mockImplementation(async (opt: boolean) => ({
      id: 'u1',
      phone: '+7 777 123 45 67',
      email: 'user@example.com',
      is_phone_verified: true,
      is_email_verified: false,
      created_at: '',
      updated_at: '',
      privacy_policy_accepted_at: '2025-06-01T12:00:00Z',
      marketing_opt_in: opt,
      marketing_opt_in_at: opt ? '2026-01-01T12:00:00Z' : null,
    }));
    mockPush.mockClear();
    mockReplace.mockClear();
    vi.mocked(logoutAuth).mockClear();
  });

  afterEach(() => {
    window.localStorage.removeItem('ringoo_access_token');
    window.localStorage.removeItem('ringoo_refresh_token');
  });

  it('shows loading then user info when authenticated', async () => {
    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Личный кабинет')).toBeInTheDocument();
    });

    expect(screen.getAllByText(/\+7 777 123 45 67/).length).toBeGreaterThan(0);
  });

  it('shows orders to rate and link to orders list', async () => {
    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByText('Заказ R-1001')).toBeInTheDocument();
    });
    expect(screen.getByRole('link', { name: /Мои заказы/ })).toHaveAttribute('href', '/orders');
    expect(screen.getByRole('link', { name: /Оценить заказ/ })).toBeInTheDocument();
  });

  it('shows addresses link and ratings block', async () => {
    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Адреса доставки/ })).toHaveAttribute(
        'href',
        '/profile/addresses'
      );
    });
    expect(screen.getByRole('heading', { name: 'Оцените работу менеджеров' })).toBeInTheDocument();
  });

  it('logout clears tokens and redirects to home', async () => {
    const user = userEvent.setup();
    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Выйти из аккаунта/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Выйти из аккаунта/ }));
    await user.click(screen.getByRole('button', { name: 'Да, выйти' }));

    expect(logoutAuth).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith('/');
  });

  it('redirects to login when session is invalid', async () => {
    window.localStorage.setItem('ringoo_access_token', 'expired-token');
    vi.mocked(getMe).mockRejectedValue({ response: { status: 401 } });

    renderWithClient(<ProfilePage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/login?next=%2Fprofile');
    });
  });
});
