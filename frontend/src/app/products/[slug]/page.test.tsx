import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ProductDetail } from '@/types';
import ProductPage from './page';

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn().mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }),
}));

vi.mock('@/lib/hooks/useProducts', () => ({
  useProduct: () => ({
    data: {
      id: '1',
      title: 'Тестовый товар',
      slug: 'test',
      price: '1000.00',
      old_price: '1200.00',
      rating: 4.5,
      reviews_count: 10,
      category: {
        id: 'cat1',
        title: 'Категория',
        slug: 'cat',
        parent: null,
        description: null,
      },
      short_description: 'Краткое описание',
      images: [],
      discount_percent: 20,
      is_featured: false,
      sku: 'SKU-1',
      description: 'Описание товара',
      brand: 'Бренд',
      is_active: true,
      specs: [],
      stock: [],
      is_in_user_cart: false,
      created_at: '',
      updated_at: '',
    } as ProductDetail,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('ProductPage', () => {
  it('renders product title', () => {
    renderWithClient(<ProductPage params={{ slug: 'test' }} />);

    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
  });
});
