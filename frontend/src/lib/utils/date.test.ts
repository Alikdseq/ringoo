import { describe, it, expect } from 'vitest';
import { formatDate } from './date';

describe('formatDate', () => {
  it('formats ISO string with default pattern', () => {
    expect(formatDate('2025-02-15')).toBe('15.02.2025');
  });

  it('formats Date object', () => {
    expect(formatDate(new Date('2025-03-10'))).toBe('10.03.2025');
  });

  it('uses custom pattern', () => {
    expect(formatDate('2025-02-15', 'yyyy-MM-dd')).toBe('2025-02-15');
  });
});
