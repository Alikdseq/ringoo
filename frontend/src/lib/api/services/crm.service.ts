import { apiClient } from '@/lib/api/client';

export interface MissingProductRequestPayload {
  product_name: string;
  contact_name?: string;
  contact_phone: string;
  contact_email?: string;
  comment?: string;
  consent_personal_data: boolean;
  consent_marketing?: boolean;
}

export interface MissingProductRequestResponse {
  id: string;
  product_name: string;
  contact_name: string;
  contact_phone: string;
  contact_email?: string | null;
  comment?: string | null;
}

export async function createMissingProductRequest(
  payload: MissingProductRequestPayload
): Promise<MissingProductRequestResponse> {
  const { data } = await apiClient.post<MissingProductRequestResponse>(
    '/crm/missing-product/',
    payload
  );
  return data;
}
