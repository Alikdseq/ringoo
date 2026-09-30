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
  items: { product_id: string; quantity: number }[];
  total_amount: string;
  delivery_cost: string;
  bonus_used: string;
  comment?: string | null;
  consent_personal_data: boolean;
  consent_marketing?: boolean;
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

/** Повтор заказа: добавить все позиции заказа в корзину. Только для авторизованных. */
export async function reorderOrder(orderId: string): Promise<Cart> {
  const { data } = await apiClient.post<Cart>(`/orders/${orderId}/reorder/`);
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

export async function updateOrderStatus(id: string, status: string): Promise<Order> {
  const { data } = await apiClient.patch<Order>(`/admin/orders/${id}/`, { status });
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
export async function trackOrder(orderNumber: string, phone: string): Promise<Order> {
  const { data } = await apiClient.get<Order>('/orders/track/', {
    params: { order_number: orderNumber, phone },
  });
  return data;
}

/**
 * Официальная форма «Проверить заказ»: POST /orders/status/
 * (Алиас к /orders/track/, чтобы не светить параметры в URL и следовать ТЗ.)
 */
export async function checkOrderStatus(orderNumber: string, phone: string): Promise<Order> {
  const { data } = await apiClient.post<Order>('/orders/status/', {
    order_number: orderNumber,
    phone,
  });
  return data;
}

/**
 * Отмена заказа. Для гостя нужны order_number + phone, для авторизованного — достаточно id.
 */
export async function cancelOrder(
  orderId: string,
  payload?: { order_number?: string; phone?: string }
): Promise<Order> {
  const { data } = await apiClient.post<Order>(`/orders/${orderId}/cancel/`, payload ?? {});
  return data;
}
