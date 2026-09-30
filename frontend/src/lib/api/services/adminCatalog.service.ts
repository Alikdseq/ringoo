import { apiClient } from '@/lib/api/client';
import type { Category } from '@/types';

export interface AdminCategory extends Category {
  is_active: boolean;
  sort_order: number;
  meta_title?: string | null;
  meta_description?: string | null;
  image?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryPayload {
  title: string;
  slug: string;
  parent?: string | null;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
  meta_title?: string | null;
  meta_description?: string | null;
}

function buildCategoryFormData(payload: CategoryPayload, imageFile?: File | null) {
  const formData = new FormData();
  formData.append('title', payload.title);
  formData.append('slug', payload.slug);
  if (payload.parent) {
    formData.append('parent', payload.parent);
  } else {
    formData.append('parent', '');
  }
  if (payload.description != null) {
    formData.append('description', payload.description);
  }
  if (typeof payload.sort_order === 'number') {
    formData.append('sort_order', String(payload.sort_order));
  }
  if (typeof payload.is_active === 'boolean') {
    formData.append('is_active', String(payload.is_active));
  }
  if (payload.meta_title != null) {
    formData.append('meta_title', payload.meta_title);
  }
  if (payload.meta_description != null) {
    formData.append('meta_description', payload.meta_description);
  }
  if (imageFile) {
    formData.append('image', imageFile);
  }
  return formData;
}

export async function getAdminCategories(): Promise<AdminCategory[]> {
  const { data } = await apiClient.get<AdminCategory[]>('/admin/products/categories/');
  return Array.isArray(data) ? data : [];
}

export async function createAdminCategory(
  payload: CategoryPayload,
  imageFile?: File | null
): Promise<AdminCategory> {
  const formData = buildCategoryFormData(payload, imageFile);
  const { data } = await apiClient.post<AdminCategory>(
    '/admin/products/categories/create/',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function updateAdminCategory(
  id: string,
  payload: CategoryPayload,
  imageFile?: File | null
): Promise<AdminCategory> {
  const formData = buildCategoryFormData(payload, imageFile);
  const { data } = await apiClient.patch<AdminCategory>(
    `/admin/products/categories/${id}/patch/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function deleteAdminCategory(id: string): Promise<void> {
  await apiClient.delete(`/admin/products/categories/${id}/patch/`);
}
