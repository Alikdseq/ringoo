/**
 * Форматирование дат из API (ISO) без hydration mismatch:
 * сервер в Docker (UTC) и браузер пользователя иначе сдвигают календарный день.
 */

function parseCalendarUtc(iso: string): Date | null {
  const trimmed = iso.trim();
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(trimmed);
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]);
  const d = Number(m[3]);
  if (!y || !mo || !d) return null;
  return new Date(Date.UTC(y, mo - 1, d));
}

/** «21 мая 2026 г.» — стабильно на SSR и клиенте */
export function formatRuDateLong(iso: string | null | undefined): string {
  if (!iso) return '—';
  const cal = parseCalendarUtc(iso);
  const date = cal ?? new Date(iso);
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/** «21.05.2026» */
export function formatRuDateShort(iso: string | null | undefined): string {
  if (!iso) return '—';
  const cal = parseCalendarUtc(iso);
  const date = cal ?? new Date(iso);
  return date.toLocaleDateString('ru-RU', { timeZone: 'UTC' });
}
