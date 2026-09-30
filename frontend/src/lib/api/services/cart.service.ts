import { apiClient } from '@/lib/api/client';
import type { Cart } from '@/types';

export async function getCart(): Promise<Cart> {
  const { data } = await apiClient.get<Cart>('/cart/');
  return data;
}

export async function addToCart(
  productId: string,
  quantity: number,
  storeId?: string,
  colorId?: string
): Promise<Cart> {
  const { data } = await apiClient.post<Cart>('/cart/items/', {
    product: productId,
    quantity,
    store: storeId ?? null,
    color: colorId ?? null,
  });
  return data;
}

export async function updateCartItem(itemId: string, quantity: number): Promise<Cart> {
  const { data } = await apiClient.patch<Cart>(`/cart/items/${itemId}/`, {
    quantity,
  });
  return data;
}

export async function removeCartItem(itemId: string): Promise<void> {
  await apiClient.delete(`/cart/items/${itemId}/`);
}

export async function clearCart(): Promise<void> {
  await apiClient.post('/cart/clear/');
}
