import { describe, expect, it } from 'vitest';
import { getFriendlyErrorMessage } from './errors';

describe('getFriendlyErrorMessage', () => {
  it('returns throttling message for HTTP 429', () => {
    expect(
      getFriendlyErrorMessage({
        response: { status: 429, data: { detail: 'Повторите позже.' } },
      })
    ).toBe('Повторите позже.');
    expect(
      getFriendlyErrorMessage({
        response: { status: 429, data: {} },
      })
    ).toContain('Слишком много запросов');
  });
});
