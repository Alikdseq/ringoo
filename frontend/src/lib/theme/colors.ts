// DESIGN_SPEC §2.1: цветовая палитра Ringoo — зелёный акцент по ТЗ

export const COLORS = {
  brand: '#22c55e',
  brandSoft: '#bbf7d0',
  brandMuted: '#14532d',

  background: '#f9fafb',
  backgroundAlt: '#ffffff',
  foreground: '#020617',
  foregroundMuted: '#64748b',
  foregroundSubtle: '#94a3b8',
  border: '#e2e8f0',
  borderDark: '#cbd5e1',
} as const;

export const SEMANTIC_COLORS = {
  success: COLORS.brand,
  danger: '#ef4444',
  warning: '#f97316',
  info: '#0ea5e9',
} as const;
