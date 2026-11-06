import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UiModeProvider } from '@/lib/providers/UiModeProvider';
import type { ProductDetail } from '@/types';
import ProductPage from './page';

const { product } = vi.hoisted(() => {
  const product = {
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
  } as ProductDetail;
  return { product };
});

vi.mock('@/lib/api/services/products.service', () => ({
  fetchProductDetailServer: vi.fn(async () => product),
}));

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
    data: product,
    isLoading: false,
    isError: false,
  }),
}));

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <UiModeProvider initialMode="official">{ui}</UiModeProvider>
    </QueryClientProvider>
  );
}

describe('ProductPage', () => {
  it('renders product title', async () => {
    const page = await ProductPage({ params: Promise.resolve({ slug: 'test' }) });
    renderWithClient(page);

    expect(screen.getByText('Тестовый товар')).toBeInTheDocument();
  });
});
