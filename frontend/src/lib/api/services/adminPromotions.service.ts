import { apiClient, type PaginatedResponse } from '@/lib/api/client';

export interface AdminPromotionListItem {
  id: string;
  title: string;
  description?: string | null;
  discount_type: 'percent' | 'fixed';
  discount_value: string;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminPromoCodeListItem {
  id: string;
  code: string;
  discount_type: 'percent' | 'fixed';
  discount_value: string;
  used_count: number;
  max_uses: number | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
}

export interface AdminPromotionPayload {
  title: string;
  description?: string | null;
  discount_type: 'percent' | 'fixed';
  discount_value: string;
  start_date: string;
  end_date: string;
  is_active?: boolean;
}

export interface AdminPromoCodePayload {
  code: string;
  discount_type: 'percent' | 'fixed';
  discount_value: string;
  max_uses?: number | null;
  min_order_amount?: string | null;
  start_date: string;
  end_date: string;
  is_active?: boolean;
}

export async function getAdminPromotions(): Promise<PaginatedResponse<AdminPromotionListItem>> {
  const { data } =
    await apiClient.get<PaginatedResponse<AdminPromotionListItem>>('/admin/promotions/');
  return data;
}

export async function createAdminPromotion(
  payload: AdminPromotionPayload
): Promise<AdminPromotionListItem> {
  const { data } = await apiClient.post<AdminPromotionListItem>(
    '/admin/promotions/create/',
    payload
  );
  return data;
}

export async function updateAdminPromotion(
  id: string,
  payload: Partial<AdminPromotionPayload>
): Promise<AdminPromotionListItem> {
  const { data } = await apiClient.patch<AdminPromotionListItem>(
    `/admin/promotions/${id}/`,
    payload
  );
  return data;
}

export async function deleteAdminPromotion(id: string): Promise<void> {
  await apiClient.delete(`/admin/promotions/${id}/`);
}

export async function getAdminPromoCodes(): Promise<PaginatedResponse<AdminPromoCodeListItem>> {
  const { data } =
    await apiClient.get<PaginatedResponse<AdminPromoCodeListItem>>('/admin/promocodes/');
  return data;
}

export async function createAdminPromoCode(
  payload: AdminPromoCodePayload
): Promise<AdminPromoCodeListItem> {
  const { data } = await apiClient.post<AdminPromoCodeListItem>(
    '/admin/promocodes/create/',
    payload
  );
  return data;
}

export async function updateAdminPromoCode(
  id: string,
  payload: Partial<AdminPromoCodePayload>
): Promise<AdminPromoCodeListItem> {
  const { data } = await apiClient.patch<AdminPromoCodeListItem>(
    `/admin/promocodes/${id}/`,
    payload
  );
  return data;
}

export async function deleteAdminPromoCode(id: string): Promise<void> {
  await apiClient.delete(`/admin/promocodes/${id}/`);
}
