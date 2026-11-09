/**
 * UI-флаг возвратов (витрина + Next Admin).
 * Включён только при явном NEXT_PUBLIC_RETURNS_ENABLED=1|true|yes.
 * Backend зеркало: RETURNS_ENABLED (см. docs/audit/REFUNDS_TEMPORARILY_DISABLED.md).
 */
export function isReturnsUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_RETURNS_ENABLED || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}
