import { apiClient } from '@/lib/api/client';
import { getApiV1BaseUrl } from '@/lib/site-url';
import type { PaginatedResponse, Product, Stock, Store } from '@/types';

const SERVER_REVALIDATE = 300;

export interface ManagerStore {
  id: string;
  name: string;
  slug?: string;
  address: string;
  city: string;
}

export interface Manager {
  id: string;
  name: string;
  slug: string;
  job_title?: string;
  photo?: string | null;
  store: ManagerStore;
  average_rating: number;
  ratings_count: number;
}

export interface ManagerDetail extends Manager {
  bio?: string;
  photo_alt?: string;
  photo_2?: string | null;
  photo_2_alt?: string;
}

export interface ManagerReview {
  id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface StoreImage {
  id: string;
  image: string;
  alt_text: string;
  sort_order: number;
}

export interface StoreManagerBrief {
  id: string;
  name: string;
  slug: string;
  job_title?: string;
  photo?: string | null;
  average_rating: number;
  ratings_count: number;
}

export interface StorePage extends Store {
  email?: string | null;
  description?: string;
  meta_title?: string;
  meta_description?: string;
  images?: StoreImage[];
  managers?: StoreManagerBrief[];
}

export async function getManagers(): Promise<Manager[]> {
  const { data } = await apiClient.get<Manager[] | PaginatedResponse<Manager>>('/stores/managers/');
  return Array.isArray(data) ? data : (data?.results ?? []);
}

export async function getStores(
  params: { city?: string; is_active?: boolean } = {}
): Promise<PaginatedResponse<Store>> {
  const query = {
    ...params,
    is_active: typeof params.is_active === 'boolean' ? String(params.is_active) : undefined,
  };
  const { data } = await apiClient.get<PaginatedResponse<Store>>('/stores/', {
    params: query,
  });
  return data;
}

export async function getStoreDetail(id: string): Promise<Store> {
  const { data } = await apiClient.get<Store>(`/stores/${id}/`);
  return data;
}

export async function getStoreBySlug(slug: string): Promise<StorePage> {
  const { data } = await apiClient.get<StorePage>(`/stores/by-slug/${encodeURIComponent(slug)}/`);
  return data;
}

export async function fetchStoreBySlugServer(slug: string): Promise<StorePage | null> {
  const base = getApiV1BaseUrl();
  const res = await fetch(`${base}/stores/by-slug/${encodeURIComponent(slug)}/`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) return null;
  return res.json() as Promise<StorePage>;
}

export async function getStoreProducts(
  slug: string,
  page = 1
): Promise<PaginatedResponse<Product>> {
  const { data } = await apiClient.get<PaginatedResponse<Product>>(
    `/stores/by-slug/${encodeURIComponent(slug)}/products/`,
    { params: { page } }
  );
  return data;
}

export async function getManagerBySlug(slug: string): Promise<ManagerDetail> {
  const { data } = await apiClient.get<ManagerDetail>(
    `/stores/managers/by-slug/${encodeURIComponent(slug)}/`
  );
  return data;
}

export async function fetchManagerBySlugServer(slug: string): Promise<ManagerDetail | null> {
  const base = getApiV1BaseUrl();
  const res = await fetch(`${base}/stores/managers/by-slug/${encodeURIComponent(slug)}/`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) return null;
  return res.json() as Promise<ManagerDetail>;
}

export async function getManagerReviews(slug: string): Promise<ManagerReview[]> {
  const { data } = await apiClient.get<ManagerReview[] | PaginatedResponse<ManagerReview>>(
    `/stores/managers/by-slug/${encodeURIComponent(slug)}/reviews/`
  );
  return Array.isArray(data) ? data : (data?.results ?? []);
}

/**
 * Остатки товара по магазинам.
 */
export async function getProductStock(productId: string): Promise<Stock[]> {
  const { data } = await apiClient.get<PaginatedResponse<Stock> | Stock[]>(
    `/products/products/${productId}/stock/`
  );
  return Array.isArray(data) ? data : (data?.results ?? []);
}
