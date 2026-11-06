import { apiClient } from '@/lib/api/client';

export interface PaymentInfo {
  id: string;
  order_id: string;
  order_number: string;
  provider: string;
  status: string;
  amount: string;
  amount_kopecks: number;
  currency: string;
  merchant_order_number: string;
  sber_order_id: string | null;
  yookassa_payment_id?: string | null;
  is_test?: boolean;
  form_url: string;
  sber_order_status: number | null;
  action_code: number | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InitiatePaymentResponse {
  payment: PaymentInfo;
  /** URL редиректа на платёжную страницу (Сбер formUrl / ЮKassa confirmation_url) */
  form_url: string;
  confirmation_url?: string;
  reused: boolean;
}

export interface PaymentStatusResponse {
  payment: PaymentInfo;
  order_status: string;
  order_payment_type?: string;
  sync_error?: string;
  code?: string;
}

export type PayGuestAuth = {
  phone: string;
  order_number: string;
  /** SEC-006: криптостойкий guest access token */
  guest_token?: string;
};

const PAY_AUTH_KEY = 'ringoo_pay_auth';
const GUEST_TOKEN_BY_ORDER_KEY = 'ringoo_guest_token_by_order';

/** Сохранить auth гостя для pay/cancel/return (sessionStorage, не в аналитику). */
export function stashPayAuth(orderId: string, auth: PayGuestAuth): void {
  try {
    sessionStorage.setItem(`${PAY_AUTH_KEY}:${orderId}`, JSON.stringify(auth));
    if (auth.order_number && auth.guest_token) {
      sessionStorage.setItem(
        `${GUEST_TOKEN_BY_ORDER_KEY}:${auth.order_number}`,
        auth.guest_token
      );
    }
  } catch {
    /* private mode */
  }
}

/** SEC-006: guest_token по номеру заказа (sessionStorage). */
export function stashGuestTokenByOrderNumber(orderNumber: string, token: string): void {
  try {
    if (!orderNumber || !token) return;
    sessionStorage.setItem(`${GUEST_TOKEN_BY_ORDER_KEY}:${orderNumber}`, token);
  } catch {
    /* private mode */
  }
}

export function peekGuestTokenByOrderNumber(orderNumber: string): string | undefined {
  try {
    return sessionStorage.getItem(`${GUEST_TOKEN_BY_ORDER_KEY}:${orderNumber}`) || undefined;
  } catch {
    return undefined;
  }
}

/** @deprecated используйте stashPayAuth */
export function stashPayPhone(orderId: string, phone: string): void {
  stashPayAuth(orderId, { phone, order_number: '' });
}

export function takePayAuth(orderId: string): PayGuestAuth | null {
  try {
    const key = `${PAY_AUTH_KEY}:${orderId}`;
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PayGuestAuth>;
    if (parsed?.phone && parsed?.order_number) {
      return {
        phone: parsed.phone,
        order_number: parsed.order_number,
        guest_token: parsed.guest_token || undefined,
      };
    }
    // legacy: только phone
    if (typeof raw === 'string' && raw && !raw.startsWith('{')) {
      return null;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function takePayPhone(orderId: string): string | null {
  return takePayAuth(orderId)?.phone ?? null;
}

/** Онлайн-оплата на витрине: только при явном NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=1 */
export function isOnlinePaymentUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED || '').trim().toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

export async function initiateOrderPayment(
  orderId: string,
  payload?: { phone?: string; order_number?: string; guest_token?: string }
): Promise<InitiatePaymentResponse> {
  const { data } = await apiClient.post<InitiatePaymentResponse>(
    `/orders/${orderId}/pay/`,
    payload ?? {}
  );
  return data;
}

export async function getOrderPaymentStatus(
  orderId: string,
  params?: { phone?: string; order_number?: string; guest_token?: string }
): Promise<PaymentStatusResponse> {
  const { data } = await apiClient.get<PaymentStatusResponse>(`/orders/${orderId}/payment/`, {
    params,
  });
  return data;
}
