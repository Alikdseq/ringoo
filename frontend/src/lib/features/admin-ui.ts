/**
 * Флаги видимости пунктов Next Admin.
 * По умолчанию OFF — каталог из 1С, без XLSX / возвратов / backup в меню.
 * Восстановление: NEXT_PUBLIC_* = 1 и пересборка frontend.
 */
function envOn(name: string): boolean {
  const v = (process.env[name] || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

export function isXlsxImportUiEnabled(): boolean {
  return envOn('NEXT_PUBLIC_XLSX_IMPORT_ENABLED');
}

/** Резервное копирование: только прямой URL + superuser; в меню не показываем. */
export function isBackupNavEnabled(): boolean {
  return envOn('NEXT_PUBLIC_BACKUP_NAV_ENABLED');
}

export { isReturnsUiEnabled } from './returns';
