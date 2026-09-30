import {
  useInfiniteQuery,
  useQuery,
  type InfiniteData,
  type UseInfiniteQueryOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';
import type { Category, PaginatedResponse, Product, ProductDetail } from '@/types';
import {
  getBrands,
  getCategories,
  getProductDetail,
  getProductModels,
  getProducts,
  type ProductFilters,
  type ProductModelsParams,
} from '@/lib/api/services/products.service';

export function useProducts(
  filters: ProductFilters,
  options?: Omit<
    UseInfiniteQueryOptions<
      PaginatedResponse<Product>,
      Error,
      InfiniteData<PaginatedResponse<Product>>,
      readonly unknown[],
      number
    >,
    'queryKey' | 'queryFn' | 'initialPageParam' | 'getNextPageParam'
  >
) {
  return useInfiniteQuery({
    queryKey: ['products', filters],
    queryFn: ({ pageParam }) => getProducts({ ...filters, page: pageParam as number }),
    initialPageParam: 1,
    staleTime: 5 * 60 * 1000,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((acc, p) => acc + p.results.length, 0);
      if (loaded >= lastPage.count) return undefined;
      return allPages.length + 1;
    },
    ...options,
  });
}

export function useProduct(
  slug: string,
  options?: Omit<
    UseQueryOptions<ProductDetail, Error, ProductDetail, readonly unknown[]>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: ['product', slug],
    queryFn: () => getProductDetail(slug),
    ...options,
  });
}

export function useCategories(
  options?: Omit<
    UseQueryOptions<Category[], Error, Category[], readonly unknown[]>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

export function useProductModels(
  params: ProductModelsParams,
  options?: Omit<
    UseQueryOptions<
      Awaited<ReturnType<typeof getProductModels>>,
      Error,
      Awaited<ReturnType<typeof getProductModels>>,
      readonly unknown[]
    >,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: ['product-models', params],
    queryFn: () => getProductModels(params),
    staleTime: 60 * 1000,
    ...options,
  });
}

export function useBrands(
  options?: Omit<
    UseQueryOptions<string[], Error, string[], readonly unknown[]>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: ['brands'],
    queryFn: getBrands,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}
