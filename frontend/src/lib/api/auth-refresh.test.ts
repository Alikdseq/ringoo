import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const postMock = vi.fn();
const createMock = vi.fn(() => ({ post: postMock }));

vi.mock('axios', async importOriginal => {
  const actual = await importOriginal<typeof import('axios')>();
  const mocked = Object.assign(
    (...args: Parameters<typeof actual.default>) => actual.default(...args),
    actual.default,
    { create: createMock }
  );
  return {
    ...actual,
    default: mocked,
  };
});

describe('refreshAccessToken (B8-002 / B8-006)', () => {
  beforeEach(() => {
    vi.resetModules();
    postMock.mockReset();
    createMock.mockClear();
    createMock.mockImplementation(() => ({ post: postMock }));
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('Bearer mode: refresh request does NOT send X-Auth-Cookies and stores access', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '0');
    localStorage.setItem('ringoo_refresh_token', 'old-refresh');
    postMock.mockResolvedValue({
      data: { access: 'new-access', refresh: 'new-refresh' },
    });

    const { refreshAccessToken } = await import('./auth-refresh');
    const access = await refreshAccessToken();

    expect(access).toBe('new-access');
    const cfg = createMock.mock.calls[0]?.[0] as { headers?: Record<string, string> };
    expect(cfg?.headers?.['X-Auth-Cookies']).toBeUndefined();
    expect(localStorage.getItem('ringoo_access_token')).toBe('new-access');
    expect(localStorage.getItem('ringoo_refresh_token')).toBe('new-refresh');
  });

  it('cookie mode: refresh sends X-Auth-Cookies and clears hint on failure', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '1');
    sessionStorage.setItem('ringoo_auth_hint', '1');
    postMock.mockRejectedValue({ response: { status: 401 } });

    const { refreshAccessToken } = await import('./auth-refresh');
    const access = await refreshAccessToken();

    expect(access).toBeNull();
    const cfg = createMock.mock.calls[0]?.[0] as { headers?: Record<string, string> };
    expect(cfg?.headers?.['X-Auth-Cookies']).toBe('1');
    expect(sessionStorage.getItem('ringoo_auth_hint')).toBeNull();
  });

  it('parallel callers share one refresh (single-flight)', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '0');
    localStorage.setItem('ringoo_refresh_token', 'r1');

    let resolvePost: (v: unknown) => void = () => undefined;
    postMock.mockImplementation(
      () =>
        new Promise(resolve => {
          resolvePost = resolve;
        })
    );

    const { refreshAccessToken } = await import('./auth-refresh');
    const p1 = refreshAccessToken();
    const p2 = refreshAccessToken();
    expect(postMock).toHaveBeenCalledTimes(1);

    resolvePost({ data: { access: 'a2', refresh: 'r2' } });
    await expect(Promise.all([p1, p2])).resolves.toEqual(['a2', 'a2']);
    expect(postMock).toHaveBeenCalledTimes(1);
  });

  it('invalidatePendingAuthRefresh drops in-flight result after logout', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '0');
    localStorage.setItem('ringoo_refresh_token', 'r1');

    let resolvePost: (v: unknown) => void = () => undefined;
    postMock.mockImplementation(
      () =>
        new Promise(resolve => {
          resolvePost = resolve;
        })
    );

    const { refreshAccessToken, invalidatePendingAuthRefresh } = await import('./auth-refresh');
    const pending = refreshAccessToken();
    invalidatePendingAuthRefresh();
    localStorage.clear();
    resolvePost({ data: { access: 'should-not-apply', refresh: 'x' } });
    await expect(pending).resolves.toBeNull();
    expect(localStorage.getItem('ringoo_access_token')).toBeNull();
  });

  it('Bearer refresh with empty access body clears session', async () => {
    vi.stubEnv('NEXT_PUBLIC_USE_AUTH_COOKIES', '0');
    localStorage.setItem('ringoo_refresh_token', 'r1');
    sessionStorage.setItem('ringoo_auth_hint', '1');
    postMock.mockResolvedValue({ data: {} });

    const { refreshAccessToken } = await import('./auth-refresh');
    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(localStorage.getItem('ringoo_refresh_token')).toBeNull();
    expect(sessionStorage.getItem('ringoo_auth_hint')).toBeNull();
  });
});
