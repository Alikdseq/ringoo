import { apiClient } from '@/lib/api/client';
import { getApiV1BaseUrl } from '@/lib/site-url';
import type { Category, PaginatedResponse, Product, ProductDetail } from '@/types';

const SERVER_REVALIDATE = 300;

export async function getCategories(): Promise<Category[]> {
  const { data } = await apiClient.get<PaginatedResponse<Category> | Category[]>(
    '/products/categories/'
  );
  if (Array.isArray(data)) return data;
  return data.results;
}

const DEFAULT_PAGE_SIZE = 20;

export interface ProductFilters {
  category?: string;
  /** Фильтр по бренду (точное совпадение, без учёта регистра на бэкенде) */
  brand?: string;
  min_price?: number;
  max_price?: number;
  search?: string;
  /** Только товары в наличии (хотя бы один склад с available_quantity > 0) */
  in_stock?: boolean;
  /** Минимальный рейтинг (например 4 для «4+ звёзд») */
  rating_min?: number;
  /** Slug магазина — только товары в наличии в этом магазине */
  store?: string;
  ordering?: 'popular' | 'price_asc' | 'price_desc' | 'rating_desc' | 'created_at';
  /** Ключ линейки модели (из product-models API) */
  model?: string;
  page?: number;
  page_size?: number;
}

export interface ProductModelOption {
  key: string;
  label: string;
  count: number;
}

export type ProductModelsParams = Omit<ProductFilters, 'model' | 'page' | 'page_size' | 'ordering'>;

/** Список брендов для фильтра каталога. */
export async function getBrands(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>('/products/products/brands/');
  return Array.isArray(data) ? data : [];
}

/** Линейки моделей в текущей выборке каталога (без model в params). */
export async function getProductModels(
  params: ProductModelsParams = {}
): Promise<ProductModelOption[]> {
  const { data } = await apiClient.get<{ results: ProductModelOption[] }>(
    '/products/products/product-models/',
    { params }
  );
  return Array.isArray(data?.results) ? data.results : [];
}

export async function getProducts(
  filters: ProductFilters = {}
): Promise<PaginatedResponse<Product>> {
  const params = { page_size: DEFAULT_PAGE_SIZE, ...filters };
  const { data } = await apiClient.get<PaginatedResponse<Product>>('/products/products/', {
    params,
  });
  return data;
}

export { DEFAULT_PAGE_SIZE };

export async function getProductDetail(slug: string): Promise<ProductDetail> {
  const { data } = await apiClient.get<ProductDetail>(`/products/products/${slug}/`);
  return data;
}

export async function fetchProductDetailServer(slug: string): Promise<ProductDetail | null> {
  const base = getApiV1BaseUrl();
  const res = await fetch(`${base}/products/products/${encodeURIComponent(slug)}/`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) return null;
  return res.json() as Promise<ProductDetail>;
}

export async function fetchCategoriesServer(): Promise<Category[]> {
  const base = getApiV1BaseUrl();
  const res = await fetch(`${base}/products/categories/`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) return [];
  const data = (await res.json()) as PaginatedResponse<Category> | Category[];
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function fetchBrandsServer(): Promise<string[]> {
  const base = getApiV1BaseUrl();
  const res = await fetch(`${base}/products/products/brands/`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) return [];
  const data = (await res.json()) as string[];
  return Array.isArray(data) ? data : [];
}

export async function fetchCategoryBySlugServer(slug: string): Promise<Category | null> {
  const categories = await fetchCategoriesServer();
  return categories.find(c => c.slug === slug) ?? null;
}

export async function fetchProductsServer(
  filters: ProductFilters = {}
): Promise<PaginatedResponse<Product>> {
  const base = getApiV1BaseUrl();
  const params = new URLSearchParams();
  params.set('page_size', String(filters.page_size ?? DEFAULT_PAGE_SIZE));
  if (filters.page) params.set('page', String(filters.page));
  if (filters.category) params.set('category', filters.category);
  if (filters.brand) params.set('brand', filters.brand);
  if (filters.search) params.set('search', filters.search);
  if (filters.ordering) params.set('ordering', filters.ordering);
  if (filters.in_stock) params.set('in_stock', 'true');

  const res = await fetch(`${base}/products/products/?${params.toString()}`, {
    next: { revalidate: SERVER_REVALIDATE },
  });
  if (!res.ok) {
    return { count: 0, next: null, previous: null, results: [] };
  }
  return res.json() as Promise<PaginatedResponse<Product>>;
}

/** Элемент ответа автодополнения: id, title, slug, sku, price, image (URL). */
export interface ProductAutocompleteItem {
  id: string;
  title: string;
  slug: string;
  sku: string | null;
  price: string;
  image: string | null;
}

export async function getProductAutocomplete(q: string): Promise<ProductAutocompleteItem[]> {
  const trimmed = q.trim();
  if (!trimmed) return [];
  const { data } = await apiClient.get<ProductAutocompleteItem[]>(
    '/products/products/autocomplete/',
    { params: { q: trimmed.slice(0, 100) } }
  );
  return Array.isArray(data) ? data : [];
}
