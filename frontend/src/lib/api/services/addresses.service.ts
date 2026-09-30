import { apiClient } from '@/lib/api/client';
import type { PaginatedResponse } from '@/lib/api/client';
import type { DeliveryAddress } from '@/types';

export async function getAddresses(): Promise<DeliveryAddress[]> {
  const { data } = await apiClient.get<DeliveryAddress[] | PaginatedResponse<DeliveryAddress>>(
    '/auth/addresses/'
  );
  return Array.isArray(data) ? data : (data?.results ?? []);
}

export interface CreateAddressBody {
  title: string;
  city: string;
  street: string;
  house: string;
  apartment?: string | null;
  postal_code?: string | null;
  is_default?: boolean;
  latitude?: string | null;
  longitude?: string | null;
}

export async function createAddress(body: CreateAddressBody): Promise<DeliveryAddress> {
  const { data } = await apiClient.post<DeliveryAddress>('/auth/addresses/', body);
  return data;
}

export async function updateAddress(
  id: number,
  body: Partial<CreateAddressBody>
): Promise<DeliveryAddress> {
  const { data } = await apiClient.patch<DeliveryAddress>(`/auth/addresses/${id}/`, body);
  return data;
}

export async function deleteAddress(id: number): Promise<void> {
  await apiClient.delete(`/auth/addresses/${id}/`);
}
