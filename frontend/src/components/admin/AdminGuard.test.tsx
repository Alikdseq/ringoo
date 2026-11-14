import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';

const fetchStaffAccess = vi.fn();
const useAuthMock = vi.fn();
const replace = vi.fn();
let pathname = '/admin/products';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => pathname,
}));

vi.mock('@/lib/hooks/useAuth', () => ({
  AUTH_STAFF_ACCESS_QUERY_KEY: ['auth', 'staff-access'],
  useAuth: () => useAuthMock(),
}));

vi.mock('@/lib/api/services/auth.service', () => ({
  fetchStaffAccess: (...args: unknown[]) => fetchStaffAccess(...args),
}));

vi.mock('./AdminLayout', () => ({
  AdminLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="admin-layout">{children}</div>
  ),
}));

import { AdminGuard } from './AdminGuard';

function renderGuard(ui: ReactElement = <span>SECRET_ADMIN</span>) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AdminGuard>{ui}</AdminGuard>
    </QueryClientProvider>
  );
}

describe('AdminGuard (B8-009 / Fix F)', () => {
  beforeEach(() => {
    fetchStaffAccess.mockReset();
    replace.mockReset();
    pathname = '/admin/products';
    useAuthMock.mockReturnValue({
      user: { id: 'u1', phone: '79001112233' },
      isLoading: false,
      isAuthenticated: true,
      hasToken: true,
    });
  });

  it('does not render admin content while staff-access is loading', () => {
    fetchStaffAccess.mockReturnValue(new Promise(() => undefined));
    renderGuard();
    expect(screen.queryByText('SECRET_ADMIN')).not.toBeInTheDocument();
    expect(screen.queryByTestId('admin-layout')).not.toBeInTheDocument();
    expect(screen.getByText(/Проверяем доступ/i)).toBeInTheDocument();
  });

  it('renders AdminLayout only after staff confirmed', async () => {
    fetchStaffAccess.mockResolvedValue({
      staff: true,
      is_superuser: false,
      groups: ['ringoo_catalog'],
    });
    renderGuard();
    expect(await screen.findByTestId('admin-layout')).toBeInTheDocument();
    expect(screen.getByText('SECRET_ADMIN')).toBeInTheDocument();
  });

  it('shows forbidden for non-staff 403 without admin layout', async () => {
    fetchStaffAccess.mockRejectedValue({ response: { status: 403, data: { detail: 'Forbidden' } } });
    renderGuard();
    expect(await screen.findByText('Доступ запрещён')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-layout')).not.toBeInTheDocument();
    expect(screen.queryByText('SECRET_ADMIN')).not.toBeInTheDocument();
  });

  it('redirects unauthenticated users to admin login', async () => {
    useAuthMock.mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      hasToken: false,
    });
    renderGuard();
    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith(
        expect.stringContaining('/admin/login?next=')
      );
    });
    expect(screen.queryByText('SECRET_ADMIN')).not.toBeInTheDocument();
  });

  it('redirects to login on staff-access 401', async () => {
    fetchStaffAccess.mockRejectedValue({ response: { status: 401 } });
    renderGuard();
    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith(
        expect.stringContaining('/admin/login?next=')
      );
    });
    expect(screen.queryByTestId('admin-layout')).not.toBeInTheDocument();
  });

  it('shows retryable unavailable state on 500 without treating as guest', async () => {
    fetchStaffAccess.mockRejectedValue({ response: { status: 500 } });
    renderGuard();
    expect(await screen.findByText(/Не удалось проверить доступ/i)).toBeInTheDocument();
    expect(screen.queryByTestId('admin-layout')).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalledWith('/');
  });

  it('retries staff-access after network/5xx', async () => {
    const user = userEvent.setup();
    fetchStaffAccess
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce({
        staff: true,
        is_superuser: true,
        groups: [],
      });
    renderGuard();
    expect(await screen.findByText(/Не удалось проверить доступ/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Повторить/i }));
    expect(await screen.findByTestId('admin-layout')).toBeInTheDocument();
  });

  it('passes children through on login page without staff check', () => {
    pathname = '/admin/login';
    fetchStaffAccess.mockResolvedValue({ staff: true, is_superuser: true, groups: [] });
    renderGuard(<span>LOGIN_FORM</span>);
    expect(screen.getByText('LOGIN_FORM')).toBeInTheDocument();
    expect(fetchStaffAccess).not.toHaveBeenCalled();
  });
});
