import { apiClient, type PaginatedResponse } from '@/lib/api/client';
import type { AdminStockItem } from '@/lib/api/services/adminProducts.service';

export interface StockStoreSummary {
  id: string;
  name: string;
  slug: string;
  city: string;
  is_active: boolean;
  total_skus: number;
  low_stock_count: number;
}

export interface StockCategoryRow {
  category_id: string;
  title: string;
  slug: string;
  stock_count: number;
}

export async function getStockStoresSummary(): Promise<StockStoreSummary[]> {
  const { data } = await apiClient.get<StockStoreSummary[]>('/admin/stores/stock/stores-summary/');
  return data;
}

export async function getStockByStoreCategories(storeId: string): Promise<StockCategoryRow[]> {
  const { data } = await apiClient.get<StockCategoryRow[]>(
    `/admin/stores/stock/by-store/${storeId}/categories/`
  );
  return data;
}

export async function getStockByStoreProducts(
  storeId: string,
  params: { category?: string; search?: string; page?: number } = {}
): Promise<PaginatedResponse<AdminStockItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminStockItem>>(
    `/admin/stores/stock/by-store/${storeId}/products/`,
    { params }
  );
  return data;
}
