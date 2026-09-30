import { apiClient, type PaginatedResponse } from '@/lib/api/client';
import type { ContentTag } from '@/types';

export interface AdminArticleListItem {
  id: string;
  title: string;
  slug: string;
  category: string | null;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
}

export interface AdminNewsListItem {
  id: string;
  title: string;
  slug: string;
  category: string | null;
  is_published: boolean;
  is_featured: boolean;
  published_at: string | null;
  created_at: string;
}

export interface AdminReviewListItem {
  id: string;
  product: string;
  user: string | null;
  name: string;
  rating: number;
  comment: string;
  is_approved: boolean;
  is_verified_purchase: boolean;
  created_at: string;
}

export interface AdminArticleParams {
  page?: number;
}

export interface AdminNewsParams {
  page?: number;
}

export interface AdminReviewParams {
  page?: number;
  is_approved?: string;
}

export interface AdminArticlePayload {
  title: string;
  slug: string;
  content: string;
  excerpt?: string;
  category?: string | null;
  is_published?: boolean;
  published_at?: string | null;
  tags?: string[];
}

export interface AdminNewsPayload {
  title: string;
  slug: string;
  content: string;
  excerpt?: string;
  category?: string | null;
  is_published?: boolean;
  is_featured?: boolean;
  published_at?: string | null;
  tags?: string[];
}

export async function getAdminTags(): Promise<ContentTag[]> {
  const { data } = await apiClient.get<ContentTag[]>('/admin/content/tags/');
  return Array.isArray(data) ? data : [];
}

export async function getAdminArticles(
  params: AdminArticleParams = {}
): Promise<PaginatedResponse<AdminArticleListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminArticleListItem>>(
    '/admin/content/articles/',
    { params }
  );
  return data;
}

function buildArticleFormData(payload: AdminArticlePayload, imageFile?: File | null): FormData {
  const formData = new FormData();
  formData.append('title', payload.title);
  formData.append('slug', payload.slug);
  formData.append('content', payload.content);
  if (payload.excerpt != null) {
    formData.append('excerpt', payload.excerpt);
  }
  if (payload.category != null) {
    formData.append('category', payload.category);
  }
  if (typeof payload.is_published === 'boolean') {
    formData.append('is_published', String(payload.is_published));
  }
  if (payload.published_at != null) {
    formData.append('published_at', payload.published_at);
  }
  if (payload.tags && payload.tags.length > 0) {
    for (const tagId of payload.tags) {
      formData.append('tags', tagId);
    }
  }
  if (imageFile) {
    formData.append('image', imageFile);
  }
  return formData;
}

function buildNewsFormData(payload: AdminNewsPayload, imageFile?: File | null): FormData {
  const formData = new FormData();
  formData.append('title', payload.title);
  formData.append('slug', payload.slug);
  formData.append('content', payload.content);
  if (payload.excerpt != null) {
    formData.append('excerpt', payload.excerpt);
  }
  if (payload.category != null) {
    formData.append('category', payload.category);
  }
  if (typeof payload.is_published === 'boolean') {
    formData.append('is_published', String(payload.is_published));
  }
  if (typeof payload.is_featured === 'boolean') {
    formData.append('is_featured', String(payload.is_featured));
  }
  if (payload.published_at != null) {
    formData.append('published_at', payload.published_at);
  }
  if (payload.tags && payload.tags.length > 0) {
    for (const tagId of payload.tags) {
      formData.append('tags', tagId);
    }
  }
  if (imageFile) {
    formData.append('image', imageFile);
  }
  return formData;
}

export async function getAdminNews(
  params: AdminNewsParams = {}
): Promise<PaginatedResponse<AdminNewsListItem>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminNewsListItem>>(
    '/admin/content/news/',
    { params }
  );
  return data;
}

export async function createAdminArticle(
  payload: AdminArticlePayload,
  imageFile?: File | null
): Promise<AdminArticleListItem> {
  const formData = buildArticleFormData(payload, imageFile);
  const { data } = await apiClient.post<AdminArticleListItem>(
    '/admin/content/articles/create/',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function updateAdminArticle(
  id: string,
  payload: AdminArticlePayload,
  imageFile?: File | null
): Promise<AdminArticleListItem> {
  const formData = buildArticleFormData(payload, imageFile);
  const { data } = await apiClient.patch<AdminArticleListItem>(
    `/admin/content/articles/${id}/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function deleteAdminArticle(id: string): Promise<void> {
  await apiClient.delete(`/admin/content/articles/${id}/`);
}

export async function createAdminNews(
  payload: AdminNewsPayload,
  imageFile?: File | null
): Promise<AdminNewsListItem> {
  const formData = buildNewsFormData(payload, imageFile);
  const { data } = await apiClient.post<AdminNewsListItem>(
    '/admin/content/news/create/',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function updateAdminNews(
  id: string,
  payload: AdminNewsPayload,
  imageFile?: File | null
): Promise<AdminNewsListItem> {
  const formData = buildNewsFormData(payload, imageFile);
  const { data } = await apiClient.patch<AdminNewsListItem>(
    `/admin/content/news/${id}/`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    }
  );
  return data;
}

export async function deleteAdminNews(id: string): Promise<void> {
  await apiClient.delete(`/admin/content/news/${id}/`);
}

export async function getAdminReviews(
  params: AdminReviewParams = {}
): Promise<PaginatedResponse<AdminReviewListItem>> {
  const query: Record<string, string | number | undefined> = {};
  if (params.page) {
    query.page = params.page;
  }
  if (params.is_approved) {
    query.is_approved = params.is_approved;
  }

  const { data } = await apiClient.get<PaginatedResponse<AdminReviewListItem>>(
    '/admin/content/reviews/',
    { params: query }
  );
  return data;
}

export async function updateAdminReviewApproval(
  id: string,
  isApproved: boolean
): Promise<AdminReviewListItem> {
  const { data } = await apiClient.patch<AdminReviewListItem>(
    `/admin/content/reviews/${id}/patch/`,
    { is_approved: isApproved }
  );
  return data;
}
