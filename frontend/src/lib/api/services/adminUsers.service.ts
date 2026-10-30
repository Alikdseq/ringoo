import { apiClient, type PaginatedResponse } from '@/lib/api/client';
import type { DeliveryAddress, UserProfile } from '@/types';

export interface AdminUserListItem {
  id: string;
  phone: string;
  email: string | null;
  is_active: boolean;
  is_staff: boolean;
  created_at: string;
}

export interface AdminUserListParams {
  page?: number;
  search?: string;
}

export interface AdminUserDetail {
  id: string;
  phone: string;
  email: string | null;
  is_active: boolean;
  is_staff: boolean;
  is_superuser?: boolean;
  groups: string[];
  profile: UserProfile | null;
  delivery_addresses: DeliveryAddress[];
  created_at: string;
}

export interface AdminUserUpdatePayload {
  is_active?: boolean;
  is_staff?: boolean;
  groups?: string[];
}

export const RINGOO_ADMIN_GROUPS = [
  'ringoo_orders',
  'ringoo_catalog',
  'ringoo_content',
  'ringoo_crm',
  'ringoo_reports',
  'ringoo_users',
  'ringoo_stores',
] as const;

export async function getAdminUsers(
  params: AdminUserListParams = {}
): Promise<PaginatedResponse<AdminUserListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminUserListItem>>('/admin/users/', {
    params,
  });
  return data;
}

export async function getAdminUser(id: string): Promise<AdminUserDetail> {
  const { data } = await apiClient.get<AdminUserDetail>(`/admin/users/${id}/`);
  return data;
}

export async function updateAdminUser(
  id: string,
  payload: AdminUserUpdatePayload
): Promise<AdminUserDetail> {
  const { data } = await apiClient.patch<AdminUserDetail>(`/admin/users/${id}/patch/`, payload);
  return data;
}
