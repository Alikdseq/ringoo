import { format, parseISO } from 'date-fns';

export function formatDate(value: string | Date, pattern = 'dd.MM.yyyy') {
  const date = typeof value === 'string' ? parseISO(value) : value;
  return format(date, pattern);
}
