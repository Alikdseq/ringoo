import clsx, { type ClassValue } from 'clsx';

// Универсальный helper для склейки классов
export function cn(...inputs: ClassValue[]) {
  return clsx(...inputs);
}
