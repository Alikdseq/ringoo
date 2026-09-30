import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import type { WishlistItem } from '@/types';
import {
  getWishlist,
  addToWishlist,
  removeFromWishlist,
} from '@/lib/api/services/wishlist.service';

export const WISHLIST_QUERY_KEY = ['wishlist'] as const;

export function useWishlist(options?: { enabled?: boolean }) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: WISHLIST_QUERY_KEY,
    queryFn: getWishlist,
    enabled: options?.enabled ?? true,
  });

  const addMutation = useMutation({
    mutationFn: addToWishlist,
    onSuccess: newItem => {
      queryClient.setQueryData<WishlistItem[]>(WISHLIST_QUERY_KEY, old =>
        old ? [newItem, ...old.filter(i => i.product.id !== newItem.product.id)] : [newItem]
      );
    },
  });

  const removeMutation = useMutation({
    mutationFn: removeFromWishlist,
    onSuccess: (_, productId) => {
      queryClient.setQueryData<WishlistItem[]>(WISHLIST_QUERY_KEY, old =>
        old ? old.filter(i => i.product.id !== productId) : []
      );
    },
  });

  const productIds = new Set((query.data ?? []).map(item => item.product.id));

  return {
    items: query.data ?? [],
    count: (query.data ?? []).length,
    isLoading: query.isLoading,
    isError: query.isError,
    isInWishlist: (productId: string) => productIds.has(productId),
    add: addMutation.mutateAsync,
    remove: removeMutation.mutateAsync,
    addMutation,
    removeMutation,
  };
}
