import { apiClient, type PaginatedResponse } from '@/lib/api/client';

export interface AdminStoreListItem {
  id: string;
  name: string;
  slug: string;
  address: string;
  city: string;
  phone: string | null;
  email: string | null;
  latitude: string | null;
  longitude: string | null;
  working_hours: Record<string, string> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminStorePayload {
  name: string;
  slug: string;
  address: string;
  city: string;
  phone?: string | null;
  email?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  working_hours?: Record<string, string> | null;
  is_active?: boolean;
}

export async function getAdminStores(): Promise<PaginatedResponse<AdminStoreListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminStoreListItem>>('/admin/stores/');
  return data;
}

export async function createAdminStore(payload: AdminStorePayload): Promise<AdminStoreListItem> {
  const { data } = await apiClient.post<AdminStoreListItem>('/admin/stores/create/', payload);
  return data;
}

export async function updateAdminStore(
  id: string,
  payload: Partial<AdminStorePayload>
): Promise<AdminStoreListItem> {
  const { data } = await apiClient.patch<AdminStoreListItem>(`/admin/stores/${id}/patch/`, payload);
  return data;
}

export async function deleteAdminStore(id: string): Promise<void> {
  await apiClient.delete(`/admin/stores/${id}/patch/`);
}

export interface AdminStoreImage {
  id: string;
  store: string;
  image_url: string | null;
  alt_text: string | null;
  sort_order: number;
  is_active: boolean;
}

export async function getAdminStoreImages(storeId: string): Promise<AdminStoreImage[]> {
  const { data } = await apiClient.get<AdminStoreImage[]>(`/admin/stores/${storeId}/images/`);
  return data;
}

export async function uploadAdminStoreImage(
  storeId: string,
  file: File,
  payload: { alt_text?: string; sort_order?: number; is_active?: boolean } = {}
): Promise<AdminStoreImage> {
  const formData = new FormData();
  formData.append('image', file);
  if (payload.alt_text) formData.append('alt_text', payload.alt_text);
  if (typeof payload.sort_order === 'number') {
    formData.append('sort_order', String(payload.sort_order));
  }
  if (typeof payload.is_active === 'boolean') {
    formData.append('is_active', String(payload.is_active));
  }
  const { data } = await apiClient.post<AdminStoreImage>(
    `/admin/stores/${storeId}/images/`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

export async function deleteAdminStoreImage(id: string): Promise<void> {
  await apiClient.delete(`/admin/stores/images/${id}/`);
}
