import { describe, expect, it } from 'vitest';

import { getApiErrorStatus, getFriendlyErrorMessage } from './errors';

describe('getApiErrorStatus', () => {
  it('reads axios response.status', () => {
    expect(getApiErrorStatus({ response: { status: 404 } })).toBe(404);
    expect(getApiErrorStatus({ response: { status: 403 } })).toBe(403);
    expect(getApiErrorStatus({ status: 500 })).toBe(500);
  });

  it('returns undefined for non-http errors', () => {
    expect(getApiErrorStatus(new Error('network'))).toBeUndefined();
    expect(getApiErrorStatus(null)).toBeUndefined();
  });
});

describe('getFriendlyErrorMessage status mapping', () => {
  it('maps 404/403/401', () => {
    expect(getFriendlyErrorMessage({ response: { status: 404 } })).toMatch(/не найден/i);
    expect(getFriendlyErrorMessage({ response: { status: 403 } })).toMatch(/прав/i);
    expect(getFriendlyErrorMessage({ response: { status: 401 } })).toMatch(/Войдите/i);
  });
});
