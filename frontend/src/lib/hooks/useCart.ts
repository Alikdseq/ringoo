import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import type { Cart } from '@/types';
import {
  addToCart,
  clearCart,
  getCart,
  removeCartItem,
  updateCartItem,
} from '@/lib/api/services/cart.service';

/** Ключ запроса корзины. После успешного входа вызвать queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY }). */
export const CART_QUERY_KEY = ['cart'] as const;

export function useCart(
  options?: Omit<UseQueryOptions<Cart, Error, Cart, typeof CART_QUERY_KEY>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: CART_QUERY_KEY,
    queryFn: getCart,
    ...options,
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      productId,
      quantity,
      storeId,
      colorId,
    }: {
      productId: string;
      quantity: number;
      storeId?: string;
      colorId?: string;
    }) => addToCart(productId, quantity, storeId, colorId),
    onSuccess: cart => {
      queryClient.setQueryData(CART_QUERY_KEY, cart);
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
    },
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, quantity }: { itemId: string; quantity: number }) =>
      updateCartItem(itemId, quantity),
    async onMutate(variables) {
      await queryClient.cancelQueries({ queryKey: CART_QUERY_KEY });
      const previousCart = queryClient.getQueryData<Cart>(CART_QUERY_KEY);
      if (previousCart) {
        const items = previousCart.items.map(item =>
          item.id === variables.itemId
            ? {
                ...item,
                quantity: variables.quantity,
                item_total: (parseFloat(item.price_at_add) * variables.quantity).toFixed(2),
              }
            : item
        );
        const total = items.reduce((sum, item) => sum + parseFloat(item.item_total), 0).toFixed(2);
        queryClient.setQueryData<Cart>(CART_QUERY_KEY, {
          ...previousCart,
          items,
          total_amount: total,
        });
      }
      return { previousCart };
    },
    onError(_error, _vars, context) {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_QUERY_KEY, context.previousCart);
      }
    },
    onSuccess(cart) {
      queryClient.setQueryData(CART_QUERY_KEY, cart);
    },
    onSettled() {
      queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
    },
  });
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId: string) => removeCartItem(itemId),
    async onMutate(itemId) {
      await queryClient.cancelQueries({ queryKey: CART_QUERY_KEY });
      const previousCart = queryClient.getQueryData<Cart>(CART_QUERY_KEY);
      if (previousCart) {
        const items = previousCart.items.filter(item => item.id !== itemId);
        const total = items.reduce((sum, item) => sum + parseFloat(item.item_total), 0).toFixed(2);
        queryClient.setQueryData<Cart>(CART_QUERY_KEY, {
          ...previousCart,
          items,
          total_amount: total,
        });
      }
      return { previousCart };
    },
    onError(_error, _vars, context) {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_QUERY_KEY, context.previousCart);
      }
    },
    onSettled() {
      queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
    },
  });
}

export function useClearCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: clearCart,
    async onMutate() {
      await queryClient.cancelQueries({ queryKey: CART_QUERY_KEY });
      const previousCart = queryClient.getQueryData<Cart>(CART_QUERY_KEY);
      if (previousCart) {
        queryClient.setQueryData<Cart>(CART_QUERY_KEY, {
          ...previousCart,
          items: [],
          total_amount: '0.00',
        });
      }
      return { previousCart };
    },
    onError(_error, _vars, context) {
      if (context?.previousCart) {
        queryClient.setQueryData(CART_QUERY_KEY, context.previousCart);
      }
    },
    onSettled() {
      queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
    },
  });
}
