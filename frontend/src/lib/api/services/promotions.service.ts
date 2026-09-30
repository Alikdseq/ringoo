import { apiClient, type PaginatedResponse } from '@/lib/api/client';
import type { Promotion } from '@/types';

export interface PromotionsParams {
  category?: string;
}

export async function getPromotions(params: PromotionsParams = {}): Promise<Promotion[]> {
  const { data } = await apiClient.get<PaginatedResponse<Promotion> | Promotion[]>(
    '/promotions/',
    { params }
  );
  if (Array.isArray(data)) return data;
  return data.results ?? [];
}
