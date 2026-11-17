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

const ADMIN_TZ = 'Europe/Moscow';

/** Node/ICU vs Chrome иногда ставят NNBSP/NBSP — нормализуем для SSR/hydrate. */
function normalizeLocaleSpaces(s: string): string {
  return s.replace(/[\u00a0\u202f]/g, ' ');
}

/**
 * Дата+время для админки: фиксированные locale и timeZone,
 * чтобы SSR (часто UTC в Docker) и браузер не расходились (React #418).
 */
export function formatRuDateTime(iso: string | Date | null | undefined): string {
  if (iso == null || iso === '') return '—';
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  if (Number.isNaN(date.getTime())) return '';
  return normalizeLocaleSpaces(
    date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: ADMIN_TZ,
    })
  );
}

/** Только календарная дата в Europe/Moscow (списки админки). */
export function formatRuDateAdmin(iso: string | Date | null | undefined): string {
  if (iso == null || iso === '') return '—';
  const date = typeof iso === 'string' ? new Date(iso) : iso;
  if (Number.isNaN(date.getTime())) return '';
  return normalizeLocaleSpaces(
    date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: ADMIN_TZ,
    })
  );
}
