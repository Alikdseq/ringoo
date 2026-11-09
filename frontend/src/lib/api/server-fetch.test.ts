import { afterEach, describe, expect, it, vi } from 'vitest';

describe('server-fetch internal Django headers', () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it('sets X-Forwarded-Proto for Docker internal HTTP API', async () => {
    vi.stubEnv('API_INTERNAL_V1_URL', 'http://web:8000/api/v1');
    vi.stubEnv('VERCEL', '');
    const { buildInternalDjangoFetchInit, usesInternalDjangoHttp } = await import('./server-fetch');
    expect(usesInternalDjangoHttp()).toBe(true);
    const init = buildInternalDjangoFetchInit({ next: { revalidate: 60 } });
    const headers = new Headers(init.headers);
    expect(headers.get('X-Forwarded-Proto')).toBe('https');
    expect(headers.get('Accept')).toBe('application/json');
  });

  it('does not set X-Forwarded-Proto for public HTTPS base', async () => {
    vi.stubEnv('API_INTERNAL_V1_URL', 'https://ringoo15.store/api/v1');
    vi.stubEnv('VERCEL', '');
    const { buildInternalDjangoFetchInit, usesInternalDjangoHttp } = await import('./server-fetch');
    expect(usesInternalDjangoHttp()).toBe(false);
    const init = buildInternalDjangoFetchInit();
    const headers = new Headers(init.headers);
    expect(headers.get('X-Forwarded-Proto')).toBeNull();
  });
});
