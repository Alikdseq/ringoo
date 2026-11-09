import { afterEach, describe, expect, it, vi } from 'vitest';
import { isReturnsUiEnabled } from './returns';

describe('isReturnsUiEnabled', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('is off by default', () => {
    vi.stubEnv('NEXT_PUBLIC_RETURNS_ENABLED', '');
    expect(isReturnsUiEnabled()).toBe(false);
  });

  it('is on for 1', () => {
    vi.stubEnv('NEXT_PUBLIC_RETURNS_ENABLED', '1');
    expect(isReturnsUiEnabled()).toBe(true);
  });

  it('is off for 0', () => {
    vi.stubEnv('NEXT_PUBLIC_RETURNS_ENABLED', '0');
    expect(isReturnsUiEnabled()).toBe(false);
  });
});
