import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const postMock = vi.fn();

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    post: (...args: unknown[]) => postMock(...args),
    get: vi.fn(),
    patch: vi.fn(),
  },
  invalidatePendingAuthRefresh: vi.fn(),
}));

describe('login / verifyAdminMfa session hint (B8-020)', () => {
  beforeEach(() => {
    vi.resetModules();
    postMock.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('cookie mode: does not set auth hint when admin_mfa_required', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '1');
    postMock.mockResolvedValue({
      data: {
        access: 'a',
        refresh: 'r',
        admin_mfa_required: true,
      },
    });

    const { login } = await import('./auth.service');
    await login('79001112233', 'secret', true);

    expect(sessionStorage.getItem('ringoo_auth_hint')).toBeNull();
    expect(localStorage.getItem('ringoo_auth_remember')).toBeNull();
  });

  it('cookie mode: sets auth hint when MFA not required', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '1');
    postMock.mockResolvedValue({
      data: {
        access: 'a',
        refresh: 'r',
        admin_mfa_required: false,
      },
    });

    const { login } = await import('./auth.service');
    await login('79001112233', 'secret', true);

    expect(sessionStorage.getItem('ringoo_auth_hint')).toBe('1');
    expect(localStorage.getItem('ringoo_auth_remember')).toBe('1');
  });

  it('cookie mode: verifyAdminMfa sets hint after MFA', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '1');
    postMock.mockResolvedValue({
      data: { access: 'a2', refresh: 'r2', admin_mfa: true },
    });

    const { verifyAdminMfa } = await import('./auth.service');
    await verifyAdminMfa('123456');

    expect(sessionStorage.getItem('ringoo_auth_hint')).toBe('1');
  });

  it('Bearer mode: login still stores tokens when MFA required', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '0');
    postMock.mockResolvedValue({
      data: {
        access: 'access-mfa',
        refresh: 'refresh-mfa',
        admin_mfa_required: true,
      },
    });

    const { login } = await import('./auth.service');
    await login('79001112233', 'secret');

    expect(localStorage.getItem('ringoo_access_token')).toBe('access-mfa');
    expect(localStorage.getItem('ringoo_refresh_token')).toBe('refresh-mfa');
    expect(sessionStorage.getItem('ringoo_auth_hint')).toBeNull();
  });
});
