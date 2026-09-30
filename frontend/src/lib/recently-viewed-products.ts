import type { Product, ProductDetail } from '@/types';

const STORAGE_KEY = 'ringoo_recent_products';
const MAX_ITEMS = 12;

export interface RecentProductSnapshot {
  id: string;
  slug: string;
  title: string;
  price: string;
  image: string | null;
  rating: number;
  reviews_count: number;
}

function mainImageUrl(product: ProductDetail): string | null {
  const main = product.images?.find(i => i.is_main) ?? product.images?.[0];
  return main?.image ?? null;
}

export function recordRecentlyViewedProduct(product: ProductDetail): void {
  if (typeof window === 'undefined') return;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const prev: RecentProductSnapshot[] = raw ? JSON.parse(raw) : [];
    const entry: RecentProductSnapshot = {
      id: product.id,
      slug: product.slug,
      title: product.title,
      price: product.price,
      image: mainImageUrl(product),
      rating: product.rating,
      reviews_count: product.reviews_count,
    };
    const without = prev.filter(p => p.id !== entry.id);
    const next = [entry, ...without].slice(0, MAX_ITEMS);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent('ringoo-recent-products'));
  } catch {
    /* ignore quota / private mode */
  }
}

export function readRecentlyViewedProducts(): RecentProductSnapshot[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentProductSnapshot[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Минимальный `Product` для `ProductCard` из снимка localStorage */
export function recentSnapshotToProduct(s: RecentProductSnapshot): Product {
  return {
    id: s.id,
    title: s.title,
    slug: s.slug,
    price: s.price,
    old_price: null,
    rating: s.rating,
    reviews_count: s.reviews_count,
    category: {
      id: '',
      title: '',
      slug: '',
      parent: null,
      description: null,
    },
    images: s.image
      ? [{ id: '', image: s.image, is_main: true, alt_text: s.title }]
      : [],
  };
}
