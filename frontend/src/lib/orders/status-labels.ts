/** Единые подписи статусов заказа и оплаты для витрины и админки. */

export const ORDER_STATUS_LABELS: Record<string, string> = {
  new: 'Новый заказ',
  processing: 'В обработке',
  ready: 'Готов',
  closed: 'Завершён',
  // legacy (до миграции / старые ответы)
  confirmed: 'В обработке',
  in_progress: 'В обработке',
  completed: 'Получен',
  cancelled: 'Отменён',
};

export const PAYMENT_STATUS_LABELS: Record<string, string> = {
  unpaid: 'Не оплачен',
  paid: 'Оплачен',
  refunded: 'Возвращён',
  // acquirer raw (на случай старых ответов)
  pending: 'Ожидает оплаты',
  created: 'Ожидает оплаты',
  registered: 'Ожидает оплаты',
  failed: 'Ошибка оплаты',
  expired: 'Истёк',
};

export const PAYMENT_TYPE_LABELS: Record<string, string> = {
  cash: 'Наличными',
  card_on_delivery: 'Картой при получении',
  card_on_pickup: 'Картой при получении',
  bank_transfer: 'Банковский перевод',
  online: 'Онлайн',
};

export function orderStatusLabel(
  status: string,
  opts?: { closureResult?: string | null; deliveryType?: string | null }
): string {
  if (status === 'ready') {
    return opts?.deliveryType === 'delivery' ? 'Готов к отправке' : 'Готов к выдаче';
  }
  if (status === 'closed') {
    if (opts?.closureResult === 'cancelled') return 'Отменён';
    if (opts?.closureResult === 'completed') return 'Получен';
    return 'Завершён';
  }
  return ORDER_STATUS_LABELS[status] ?? status;
}

export function paymentStatusLabel(status: string | null | undefined): string {
  if (!status) return PAYMENT_STATUS_LABELS.unpaid;
  return PAYMENT_STATUS_LABELS[status] ?? status;
}

/** FSM для админ-селекта (без legacy-кодов). */
export const ORDER_STATUS_TRANSITIONS: Record<string, string[]> = {
  new: ['processing', 'closed'],
  processing: ['ready', 'closed'],
  ready: ['closed'],
  closed: [],
  // legacy maps
  confirmed: ['ready', 'closed'],
  in_progress: ['ready', 'closed'],
  completed: [],
  cancelled: [],
};

export function allowedOrderStatusOptions(
  current: string,
  labels: Record<string, string> = ORDER_STATUS_LABELS
): { value: string; label: string }[] {
  const next = ORDER_STATUS_TRANSITIONS[current] ?? [];
  const options = [{ value: current, label: labels[current] ?? current }];
  for (const value of next) {
    if (value === 'closed') {
      options.push({ value: 'completed', label: 'Получен' });
      options.push({ value: 'cancelled', label: 'Отменён' });
    } else {
      options.push({ value, label: labels[value] ?? value });
    }
  }
  return options;
}
