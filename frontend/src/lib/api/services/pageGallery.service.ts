import { apiClient, type PaginatedResponse } from '@/lib/api/client';

export type PageGalleryPlacement = 'stores_hero' | 'about_hero';

export interface PageGalleryImage {
  id: string;
  placement: PageGalleryPlacement;
  image: string;
  alt_text: string;
  sort_order: number;
}

export interface AdminPageGalleryImage extends PageGalleryImage {
  is_active: boolean;
  created_at: string;
}

export async function getPageGallery(placement: PageGalleryPlacement): Promise<PageGalleryImage[]> {
  const { data } = await apiClient.get<PageGalleryImage[]>('/content/page-gallery/', {
    params: { placement },
  });
  return Array.isArray(data) ? data : [];
}

export async function getAdminPageGallery(
  placement?: PageGalleryPlacement
): Promise<PaginatedResponse<AdminPageGalleryImage>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminPageGalleryImage>>(
    '/admin/content/page-gallery/',
    { params: placement ? { placement } : undefined }
  );
  return data;
}

export async function createAdminPageGallery(formData: FormData): Promise<AdminPageGalleryImage> {
  const { data } = await apiClient.post<AdminPageGalleryImage>(
    '/admin/content/page-gallery/create/',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

export async function updateAdminPageGallery(
  id: string,
  formData: FormData
): Promise<AdminPageGalleryImage> {
  const { data } = await apiClient.patch<AdminPageGalleryImage>(
    `/admin/content/page-gallery/${id}/`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

export async function deleteAdminPageGallery(id: string): Promise<void> {
  await apiClient.delete(`/admin/content/page-gallery/${id}/`);
}
