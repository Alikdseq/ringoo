import { apiClient, type PaginatedResponse } from '@/lib/api/client';

export interface AdminMissingProductRequest {
  id: string;
  product_name: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string | null;
  comment: string | null;
  status: string;
  created_at: string;
}

export interface AdminMissingProductParams {
  page?: number;
  status?: string;
}

export async function getAdminMissingProductRequests(
  params: AdminMissingProductParams = {}
): Promise<PaginatedResponse<AdminMissingProductRequest>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminMissingProductRequest>>(
    '/admin/crm/requests/',
    {
      params,
    }
  );
  return data;
}

export async function updateAdminMissingProductStatus(
  id: string,
  status: string
): Promise<AdminMissingProductRequest> {
  const { data } = await apiClient.patch<AdminMissingProductRequest>(
    `/admin/crm/requests/${id}/patch/`,
    { status }
  );
  return data;
}
