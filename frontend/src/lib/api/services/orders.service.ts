import { apiClient } from '@/lib/api/client';
import type { Cart, Order, PaginatedResponse } from '@/types';

/**
 * Тело POST /orders/ (поля сериализатора + from_cart для снимка позиций).
 * Итоговая сумма на сервере пересчитывается из каталога; total_amount в запросе проходит валидацию, затем заменяется.
 */
export interface CreateOrderPayload {
  /** Клиентский снимок корзины; сервер подставит цены из БД. */
  from_cart?: boolean;
  full_name: string;
  phone: string;
  email?: string | null;
  delivery_type: string;
  delivery_address?: Record<string, string | null>;
  store?: string | null;
  payment_type: string;
  items: {
    product_id: string;
    quantity: number;
    color_id?: string | null;
    expected_unit_price?: string | null;
  }[];
  total_amount: string;
  delivery_cost: string;
  bonus_used: string;
  comment?: string | null;
  consent_personal_data: boolean;
  consent_marketing?: boolean;
  /** FUNC-003: подтверждение новых цен после price_changed. */
  accept_price_changes?: boolean;
}

export interface CreateOrderOptions {
  /** Ключ идемпотентности: при повторной отправке с тем же ключом вернётся тот же заказ без дублирования. */
  idempotencyKey?: string;
}

export async function createOrder(
  orderData: CreateOrderPayload,
  options?: CreateOrderOptions
): Promise<Order> {
  const headers: Record<string, string> = {};
  if (options?.idempotencyKey) {
    headers['X-Idempotency-Key'] = options.idempotencyKey;
  }
  const { data } = await apiClient.post<Order>('/orders/', orderData, {
    headers: Object.keys(headers).length ? headers : undefined,
  });
  return data;
}

export async function getOrder(id: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/orders/${id}/`);
  return data;
}

export type ReorderSkippedItem = {
  product_title: string;
  reason: string;
  available?: number;
};

export type ReorderResult = {
  cart: Cart;
  added_count: number;
  skipped: ReorderSkippedItem[];
  partial: boolean;
};

/** Повтор заказа: color+store из заказа; актуальная цена. Только для авторизованных. */
export async function reorderOrder(orderId: string): Promise<ReorderResult> {
  const { data } = await apiClient.post<ReorderResult>(`/orders/${orderId}/reorder/`);
  return data;
}

export interface OrderListParams {
  status?: string;
  page?: number;
  payment_type?: string;
  delivery_type?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export async function getOrders(params: OrderListParams = {}): Promise<PaginatedResponse<Order>> {
  const { data } = await apiClient.get<PaginatedResponse<Order>>('/orders/', {
    params,
  });
  return data;
}

/** Админ: список всех заказов через admin_api (SEC-001, MFA + группа). */
export async function getAdminOrders(
  params: OrderListParams = {}
): Promise<PaginatedResponse<Order>> {
  const { data } = await apiClient.get<PaginatedResponse<Order>>('/admin/orders/', {
    params,
  });
  return data;
}

/** Админ: детали заказа через admin_api. */
export async function getAdminOrder(id: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/admin/orders/${id}/`);
  return data;
}

export async function updateOrderStatus(id: string, status: string): Promise<Order> {
  // Админ-UI шлёт completed/cancelled как ярлыки закрытия.
  const payload: { status: string; closure_result?: string } =
    status === 'completed' || status === 'cancelled'
      ? { status: 'closed', closure_result: status }
      : { status };
  const { data } = await apiClient.patch<Order>(`/admin/orders/${id}/`, payload);
  return data;
}

export async function exportOrdersCsv(params: OrderListParams = {}): Promise<Blob> {
  const response = await apiClient.get('/admin/orders/export/', {
    params,
    responseType: 'blob',
  });
  return response.data;
}

/**
 * Рейтинг менеджеров: средняя оценка, количество, последние отзывы (для «О нас» и ЛК).
 */
export interface RatingsSummary {
  average: number;
  count: number;
  recent: {
    rating: number;
    comment: string | null;
    created_at: string;
    manager_name?: string | null;
  }[];
}

export async function getRatingsSummary(): Promise<RatingsSummary> {
  const { data } = await apiClient.get<RatingsSummary>('/orders/ratings-summary/');
  return data;
}

/** Пayload для отправки оценки: обязательно manager_id (конкретный менеджер). */
export interface SubmitRatingPayload {
  order_id?: string;
  order_number?: string;
  phone?: string;
  manager_id: string;
  rating: number;
  comment?: string;
}

export interface ManagerRatingResponse {
  id: string;
  order: string;
  order_number: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export async function submitOrderRating(
  payload: SubmitRatingPayload
): Promise<ManagerRatingResponse> {
  const { data } = await apiClient.post<ManagerRatingResponse>('/orders/rate/', payload);
  return data;
}

/**
 * Проверка статуса заказа по номеру и телефону (гостевой заказ). Без авторизации.
 */
export async function trackOrder(
  orderNumber: string,
  phone: string,
  guestToken?: string
): Promise<Order> {
  const { data } = await apiClient.get<Order>('/orders/track/', {
    params: {
      order_number: orderNumber,
      phone,
      ...(guestToken ? { guest_token: guestToken } : {}),
    },
  });
  return data;
}

/**
 * Официальная форма «Проверить заказ»: POST /orders/status/
 * (Алиас к /orders/track/, чтобы не светить параметры в URL и следовать ТЗ.)
 */
export async function checkOrderStatus(
  orderNumber: string,
  phone: string,
  guestToken?: string
): Promise<Order> {
  const { data } = await apiClient.post<Order>('/orders/status/', {
    order_number: orderNumber,
    phone,
    ...(guestToken ? { guest_token: guestToken } : {}),
  });
  return data;
}

/**
 * Отмена заказа. Гость: обязателен guest_token (SEC-006).
 */
export async function cancelOrder(
  orderId: string,
  payload?: { order_number?: string; phone?: string; guest_token?: string }
): Promise<Order> {
  const { data } = await apiClient.post<Order>(`/orders/${orderId}/cancel/`, payload ?? {});
  return data;
}

/** SEC-006: запрос письма восстановления гостевого доступа (anti-enumeration). */
export async function requestGuestAccessRecovery(params: {
  order_number: string;
  email: string;
}): Promise<{ detail: string }> {
  const { data } = await apiClient.post<{ detail: string }>(
    '/orders/guest-access/recover/',
    {
      order_number: params.order_number.trim(),
      email: params.email.trim(),
    }
  );
  return data;
}

/** SEC-006: обмен recovery-токена на guest_access_token. */
export async function confirmGuestAccessRecovery(params: {
  order_number: string;
  token: string;
}): Promise<{ guest_access_token: string; order_id: string | null; order_number: string }> {
  const { data } = await apiClient.post<{
    guest_access_token: string;
    order_id: string | null;
    order_number: string;
  }>('/orders/guest-access/recover/confirm/', {
    order_number: params.order_number.trim(),
    token: params.token.trim(),
  });
  return data;
}
