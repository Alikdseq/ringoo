/**
 * B8-004: стабильный X-Idempotency-Key на одну логическую попытку checkout.
 * Новый ключ — только при смене состава попытки (fingerprint) или после успеха.
 */

export function createCheckoutIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `ck-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Отпечаток попытки: смена корзины/доставки/оплаты → новая логическая попытка. */
export function buildCheckoutAttemptFingerprint(input: {
  cartId?: string | null;
  paymentType: string | null;
  storeId: string | null;
  deliveryType: string;
  phone: string;
  fullName: string;
  itemKeys: string[];
  acceptPriceChanges: boolean;
}): string {
  return [
    input.cartId ?? '',
    input.paymentType ?? '',
    input.storeId ?? '',
    input.deliveryType,
    input.phone.trim(),
    input.fullName.trim(),
    input.itemKeys.join('|'),
    input.acceptPriceChanges ? '1' : '0',
  ].join('::');
}

/**
 * Возвращает ключ для текущей попытки: тот же fingerprint → тот же key.
 */
export function resolveCheckoutIdempotencyKey(state: {
  fingerprint: string;
  lastFingerprint: string | null;
  currentKey: string | null;
}): { key: string; fingerprint: string } {
  if (state.currentKey && state.lastFingerprint === state.fingerprint) {
    return { key: state.currentKey, fingerprint: state.fingerprint };
  }
  return {
    key: createCheckoutIdempotencyKey(),
    fingerprint: state.fingerprint,
  };
}
