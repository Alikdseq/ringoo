/** Промокоды на витрине/checkout — по умолчанию выкл. Акции (marketing) не затрагиваются. */
export function isPromoCodesUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_PROMOCODES_ENABLED || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

/** Блоки лояльности/бонусов в UI — по умолчанию выкл. */
export function isLoyaltyUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_LOYALTY_UI_ENABLED || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

/** Кнопка экспорта персональных данных — по умолчанию выкл. */
export function isDataExportUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_DATA_EXPORT_UI_ENABLED || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}
