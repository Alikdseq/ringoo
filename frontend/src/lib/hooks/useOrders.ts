import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type UseInfiniteQueryOptions,
  type UseQueryOptions,
} from '@tanstack/react-query';
import type { Order, PaginatedResponse } from '@/types';
import {
  createOrder,
  type CreateOrderPayload,
  getOrder,
  getOrders,
} from '@/lib/api/services/orders.service';

const ORDERS_LIST_KEY = ['orders'] as const;

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderData: CreateOrderPayload) => createOrder(orderData),
    onSuccess: order => {
      queryClient.invalidateQueries({ queryKey: ORDERS_LIST_KEY });
      queryClient.setQueryData(['order', order.id], order);
    },
    onError: error => {
      console.error('Failed to create order', error);
    },
  });
}

export function useOrder(
  id: string,
  options?: Omit<UseQueryOptions<Order, Error, Order, readonly unknown[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
    enabled: Boolean(id),
    ...options,
  });
}

export function useOrders(
  filters: { status?: string; page?: number } = {},
  options?: Omit<
    UseInfiniteQueryOptions<
      PaginatedResponse<Order>,
      Error,
      InfiniteData<PaginatedResponse<Order>>,
      readonly unknown[],
      number
    >,
    'queryKey' | 'queryFn' | 'initialPageParam' | 'getNextPageParam'
  >
) {
  return useInfiniteQuery({
    queryKey: [ORDERS_LIST_KEY[0], filters],
    queryFn: ({ pageParam }) =>
      getOrders({
        ...filters,
        page: typeof pageParam === 'number' ? pageParam : (filters.page ?? 1),
      }),
    initialPageParam: filters.page ?? 1,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, page) => sum + page.results.length, 0);
      if (loaded >= lastPage.count) return undefined;
      return (filters.page ?? 1) + allPages.length;
    },
    ...options,
  });
}
