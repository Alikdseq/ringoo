import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIsClient } from './useIsClient';

describe('useIsClient', () => {
  it('returns boolean', () => {
    const { result } = renderHook(() => useIsClient());
    expect(typeof result.current).toBe('boolean');
  });

  it('returns true in jsdom (window is defined)', () => {
    const { result } = renderHook(() => useIsClient());
    expect(result.current).toBe(true);
  });
});
