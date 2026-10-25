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
  form_url: string;
  sber_order_status: number | null;
  action_code: number | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InitiatePaymentResponse {
  payment: PaymentInfo;
  form_url: string;
  reused: boolean;
}

export interface PaymentStatusResponse {
  payment: PaymentInfo;
  order_status: string;
  order_payment_type?: string;
  sync_error?: string;
  code?: string;
}

const PAY_PHONE_KEY = 'ringoo_pay_phone';

/** Сохранить телефон для гостевой проверки статуса после возврата со Сбера. */
export function stashPayPhone(orderId: string, phone: string): void {
  try {
    sessionStorage.setItem(`${PAY_PHONE_KEY}:${orderId}`, phone);
  } catch {
    /* private mode */
  }
}

export function takePayPhone(orderId: string): string | null {
  try {
    const key = `${PAY_PHONE_KEY}:${orderId}`;
    const v = sessionStorage.getItem(key);
    return v;
  } catch {
    return null;
  }
}

export async function initiateOrderPayment(
  orderId: string,
  payload?: { phone?: string }
): Promise<InitiatePaymentResponse> {
  const { data } = await apiClient.post<InitiatePaymentResponse>(
    `/orders/${orderId}/pay/`,
    payload ?? {}
  );
  return data;
}

export async function getOrderPaymentStatus(
  orderId: string,
  params?: { phone?: string }
): Promise<PaymentStatusResponse> {
  const { data } = await apiClient.get<PaymentStatusResponse>(`/orders/${orderId}/payment/`, {
    params,
  });
  return data;
}
