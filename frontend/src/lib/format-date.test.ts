import { formatRuDateAdmin, formatRuDateTime } from './format-date';

describe('formatRuDateTime / formatRuDateAdmin', () => {
  it('formats datetime stably with Moscow timezone', () => {
    // 2026-03-15T12:00:00Z → 15.03.2026, 15:00 in Europe/Moscow (UTC+3)
    expect(formatRuDateTime('2026-03-15T12:00:00.000Z')).toBe('15.03.2026, 15:00');
  });

  it('formats date-only stably', () => {
    expect(formatRuDateAdmin('2026-03-15T12:00:00.000Z')).toBe('15.03.2026');
  });

  it('returns em dash for empty', () => {
    expect(formatRuDateTime(null)).toBe('—');
    expect(formatRuDateAdmin(undefined)).toBe('—');
  });

  it('returns empty string for invalid', () => {
    expect(formatRuDateTime('not-a-date')).toBe('');
  });
});
