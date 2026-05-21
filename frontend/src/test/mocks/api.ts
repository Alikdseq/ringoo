import type { Cart, Category, Product, ProductDetail } from '@/types';

export const mockCategory: Category = {
  id: 'cat1',
  title: 'Категория',
  slug: 'category',
  parent: null,
  description: null,
};

export const mockProduct: Product = {
  id: 'p1',
  title: 'Тестовый товар',
  slug: 'test-product',
  price: '1000.00',
  old_price: null,
  rating: 4.5,
  reviews_count: 10,
  category: mockCategory,
  images: [],
  discount_percent: undefined,
};

export const mockProductDetail: ProductDetail = {
  ...mockProduct,
  sku: 'SKU-001',
  description: 'Описание товара',
  brand: 'Brand',
  is_active: true,
  specs: [],
  stock: [],
  is_in_user_cart: false,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

export const mockCart: Cart = {
  id: 'cart1',
  items: [
    {
      id: 'item1',
      quantity: 2,
      price_at_add: '1000.00',
      item_total: '2000.00',
      created_at: '',
      updated_at: '',
      product: mockProduct,
      store: null,
    },
  ],
  total_amount: '2000.00',
  created_at: '',
  updated_at: '',
};

export const mockPaginatedProducts = {
  count: 1,
  next: null,
  previous: null,
  results: [mockProduct],
};
