/**
 * DESIGN_SPEC §3: типографика Ringoo
 * Шрифт: Geist Sans (подключён в layout.tsx)
 */

export const FONT_FAMILY_SANS =
  'var(--font-geist-sans), system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

export const FONT_FAMILY_MONO =
  'var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';

/** Семантические классы типографики (Tailwind) */
export const TYPOGRAPHY = {
  h1: 'text-h1 md:text-h1-lg font-bold tracking-tight leading-tight',
  h2: 'text-h2 font-semibold tracking-tight leading-tight',
  h3: 'text-h3 font-semibold leading-tight',

  body: 'text-body leading-normal' /* DESIGN_SPEC: 1.5 */,
  bodySmall: 'text-body-small leading-normal',
  caption: 'text-caption',
  button: 'text-button font-medium',
} as const;

/** Альтернатива для второстепенного текста */
export const TYPOGRAPHY_MUTED = {
  body: 'text-body text-foreground-muted leading-normal',
  bodySmall: 'text-body-small text-foreground-muted leading-normal',
  caption: 'text-caption text-foreground-subtle',
} as const;
