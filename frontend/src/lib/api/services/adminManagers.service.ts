import { apiClient, type PaginatedResponse } from '@/lib/api/client';

export interface AdminManagerListItem {
  id: string;
  name: string;
  slug: string;
  job_title: string;
  bio: string;
  photo: string | null;
  photo_2: string | null;
  photo_alt: string;
  photo_2_alt: string;
  store: string;
  store_name: string;
  is_active: boolean;
  order: number;
}

export interface AdminManagerForm {
  name: string;
  slug?: string;
  job_title?: string;
  bio?: string;
  store: string;
  is_active?: boolean;
  order?: number;
  photo_alt?: string;
  photo_2_alt?: string;
}

export async function getAdminManagers(params?: {
  store?: string;
  search?: string;
  is_active?: boolean;
}): Promise<PaginatedResponse<AdminManagerListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminManagerListItem>>('/admin/managers/', {
    params,
  });
  return data;
}

export function buildManagerFormData(
  payload: AdminManagerForm,
  files?: { photo?: File | null; photo_2?: File | null }
): FormData {
  const fd = new FormData();
  fd.append('name', payload.name);
  fd.append('store', payload.store);
  if (payload.slug) fd.append('slug', payload.slug);
  if (payload.job_title != null) fd.append('job_title', payload.job_title);
  if (payload.bio != null) fd.append('bio', payload.bio);
  if (payload.is_active != null) fd.append('is_active', String(payload.is_active));
  if (payload.order != null) fd.append('order', String(payload.order));
  if (payload.photo_alt != null) fd.append('photo_alt', payload.photo_alt);
  if (payload.photo_2_alt != null) fd.append('photo_2_alt', payload.photo_2_alt);
  if (files?.photo) fd.append('photo', files.photo);
  if (files?.photo_2) fd.append('photo_2', files.photo_2);
  return fd;
}

export async function createAdminManager(formData: FormData): Promise<AdminManagerListItem> {
  const { data } = await apiClient.post<AdminManagerListItem>('/admin/managers/create/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function updateAdminManager(
  id: string,
  formData: FormData
): Promise<AdminManagerListItem> {
  const { data } = await apiClient.patch<AdminManagerListItem>(`/admin/managers/${id}/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function deleteAdminManager(id: string): Promise<void> {
  await apiClient.delete(`/admin/managers/${id}/`);
}
