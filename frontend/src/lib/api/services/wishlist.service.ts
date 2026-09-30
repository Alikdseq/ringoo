import { apiClient } from '@/lib/api/client';
import type { Product, WishlistItem } from '@/types';

export async function getWishlist(): Promise<WishlistItem[]> {
  const { data } = await apiClient.get<WishlistItem[]>('/wishlist/');
  return data;
}

export async function addToWishlist(productId: string): Promise<WishlistItem> {
  const { data } = await apiClient.post<WishlistItem>('/wishlist/', {
    product_id: productId,
  });
  return data;
}

export async function removeFromWishlist(productId: string): Promise<void> {
  await apiClient.delete(`/wishlist/${productId}/`);
}
