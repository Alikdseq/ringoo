import { apiClient, type PaginatedResponse } from '@/lib/api/client';
import type { Category, ProductDetail } from '@/types';

export interface AdminProductListItem {
  id: string;
  title: string;
  slug: string;
  sku: string | null;
  category: Category;
  price: string;
  old_price: string | null;
  is_active: boolean;
  is_featured: boolean;
  brand: string | null;
  created_at: string;
  available_quantity_total: number;
}

export interface AdminProductListParams {
  page?: number;
  search?: string;
  category?: string;
  brand?: string;
  is_active?: string;
  ordering?: string;
}

export interface AdminProductPayload {
  title: string;
  slug?: string;
  sku?: string | null;
  category: string;
  brand?: string | null;
  price: string;
  old_price?: string | null;
  description?: string;
  short_description?: string | null;
  is_active?: boolean;
  is_featured?: boolean;
}

export interface AdminProductImage {
  id: string;
  product: string;
  image_url: string | null;
  /** UUID цвета (ProductColor), если привязано */
  color?: string | null;
  is_main: boolean;
  alt_text: string | null;
  sort_order: number;
}

export interface AdminProductSpec {
  id: string;
  product: string;
  name: string;
  value: string;
  sort_order: number;
}

export interface AdminStockItem {
  id: string;
  product: string;
  product_title: string;
  store: string;
  store_name: string;
  quantity: number;
  reserved_quantity: number;
  available_quantity: number;
}

export interface AdminStockListParams {
  page?: number;
  product?: string;
  store?: string;
}

export async function getAdminProducts(
  params: AdminProductListParams = {}
): Promise<PaginatedResponse<AdminProductListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminProductListItem>>(
    '/admin/products/',
    {
      params,
    }
  );
  return data;
}

export async function getAdminProduct(id: string): Promise<ProductDetail> {
  const { data } = await apiClient.get<ProductDetail>(`/admin/products/${id}/`);
  return data;
}

export async function deleteAdminProduct(id: string): Promise<void> {
  await apiClient.delete(`/admin/products/${id}/patch/`);
}

export async function createAdminProduct(payload: AdminProductPayload): Promise<ProductDetail> {
  const { data } = await apiClient.post<ProductDetail>('/admin/products/create/', payload);
  return data;
}

export async function updateAdminProduct(
  id: string,
  payload: AdminProductPayload
): Promise<ProductDetail> {
  const { data } = await apiClient.patch<ProductDetail>(`/admin/products/${id}/patch/`, payload);
  return data;
}

export interface BulkSetActivePayload {
  product_ids: string[];
  is_active: boolean;
}

export interface BulkUpdatePricesPayload {
  product_ids: string[];
  mode: 'percent' | 'absolute';
  value: number;
  direction: 'increase' | 'decrease';
  field: 'price' | 'old_price';
}

export async function bulkSetActive(payload: BulkSetActivePayload): Promise<{ updated: number }> {
  const { data } = await apiClient.post<{ updated: number }>(
    '/admin/products/bulk/set-active/',
    payload
  );
  return data;
}

export async function bulkUpdatePrices(
  payload: BulkUpdatePricesPayload
): Promise<{ updated: number }> {
  const { data } = await apiClient.post<{ updated: number }>(
    '/admin/products/bulk/update-prices/',
    payload
  );
  return data;
}

export async function exportProductsCsv(params: AdminProductListParams = {}): Promise<Blob> {
  const response = await apiClient.get('/admin/products/export/', {
    params,
    responseType: 'blob',
  });
  return response.data;
}

export async function downloadProductImportTemplate(): Promise<Blob> {
  const response = await apiClient.get('/admin/products/import/template/', {
    responseType: 'blob',
  });
  return response.data;
}

export interface BulkImportResult {
  ok: boolean;
  errors: string[];
  created: number;
  updated: number;
  images: number;
}

export async function bulkImportProducts(
  file: File,
  archive?: File | null
): Promise<BulkImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (archive) {
    formData.append('archive', archive);
  }
  const response = await apiClient.post<BulkImportResult | { detail?: string }>(
    '/admin/products/import/',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      validateStatus: status => status === 200 || status === 400,
    }
  );
  const d = response.data;
  if (response.status === 200 && d && typeof d === 'object' && 'created' in d) {
    return d as BulkImportResult;
  }
  if (response.status === 400 && d && typeof d === 'object' && 'created' in d) {
    return d as BulkImportResult;
  }
  const err = new Error('Import failed') as Error & {
    response?: { status?: number; data?: unknown };
  };
  err.response = { status: response.status, data: d };
  throw err;
}

export interface ProductImagePayload {
  alt_text?: string | null;
  is_main?: boolean;
  sort_order?: number;
}

export async function uploadProductImage(
  productId: string,
  file: File,
  payload: ProductImagePayload = {}
): Promise<AdminProductImage> {
  const formData = new FormData();
  formData.append('image', file);
  if (typeof payload.alt_text === 'string') {
    formData.append('alt_text', payload.alt_text);
  }
  if (typeof payload.is_main === 'boolean') {
    formData.append('is_main', String(payload.is_main));
  }
  if (typeof payload.sort_order === 'number') {
    formData.append('sort_order', String(payload.sort_order));
  }

  const { data } = await apiClient.post<AdminProductImage>(
    `/admin/products/${productId}/images/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function updateProductImage(
  id: string,
  payload: ProductImagePayload
): Promise<AdminProductImage> {
  const { data } = await apiClient.patch<AdminProductImage>(
    `/admin/products/images/${id}/`,
    payload
  );
  return data;
}

export async function deleteProductImage(id: string): Promise<void> {
  await apiClient.delete(`/admin/products/images/${id}/`);
}

export interface ProductSpecPayload {
  name: string;
  value: string;
  sort_order?: number;
}

export async function createProductSpec(
  productId: string,
  payload: ProductSpecPayload
): Promise<AdminProductSpec> {
  const { data } = await apiClient.post<AdminProductSpec>(
    `/admin/products/${productId}/specs/`,
    payload
  );
  return data;
}

export async function updateProductSpec(
  id: string,
  payload: ProductSpecPayload
): Promise<AdminProductSpec> {
  const { data } = await apiClient.patch<AdminProductSpec>(`/admin/products/specs/${id}/`, payload);
  return data;
}

export async function deleteProductSpec(id: string): Promise<void> {
  await apiClient.delete(`/admin/products/specs/${id}/`);
}

export async function getAdminStockByProduct(
  productId: string
): Promise<PaginatedResponse<AdminStockItem>> {
  return getAdminStock({ product: productId });
}

export async function updateAdminStock(
  id: string,
  payload: Partial<Pick<AdminStockItem, 'quantity' | 'reserved_quantity'>>
): Promise<AdminStockItem> {
  const { data } = await apiClient.patch<AdminStockItem>(`/admin/stores/stock/${id}/`, payload);
  return data;
}

export async function getAdminStock(
  params: AdminStockListParams = {}
): Promise<PaginatedResponse<AdminStockItem>> {
  const query: Record<string, string | number | undefined> = {};
  if (params.page) {
    query.page = params.page;
  }
  if (params.product) {
    query.product = params.product;
  }
  if (params.store) {
    query.store = params.store;
  }

  const { data } = await apiClient.get<PaginatedResponse<AdminStockItem>>('/admin/stores/stock/', {
    params: query,
  });
  return data;
}
