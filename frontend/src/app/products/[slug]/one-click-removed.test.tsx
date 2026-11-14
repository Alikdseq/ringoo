import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement } from 'react';
import type { ProductDetail } from '@/types';

vi.mock('next/dynamic', () => ({
  default: () => {
    const Comp = () => null;
    return Comp;
  },
}));

vi.mock('@/lib/hooks/useProducts', () => ({
  useProduct: () => ({
    data: mockProduct,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn(async () => []),
}));

vi.mock('@/lib/api/services/cart.service', () => ({
  addToCart: vi.fn(),
}));

vi.mock('@/lib/providers/UiModeProvider', () => ({
  useUiMode: () => ({ mode: 'default' }),
}));

vi.mock('@/components/ringik/Ringik', () => ({
  Ringik: () => null,
  useRingikIntersectionTrigger: () => ({ ref: { current: null }, visible: false }),
}));

vi.mock('@/components/features/products/ProductDetailRecommendations', () => ({
  ProductDetailRecommendations: () => null,
}));

vi.mock('@/components/features/products/ProductSpecsTable', () => ({
  ProductSpecsTable: () => null,
}));

vi.mock('@/components/features/products/ProductTabs', () => ({
  ProductTabs: () => null,
}));

import { ProductPageClient } from './ProductPageClient';

const mockProduct = {
  id: 'p1',
  title: 'Телефон',
  slug: 'phone',
  price: '10000.00',
  old_price: null,
  rating: 0,
  reviews_count: 0,
  description: '',
  sku: 'SKU',
  brand: 'B',
  is_active: true,
  images: [],
  specs: [],
  category: { id: 'c1', title: 'C', slug: 'c', parent: null, description: null },
  colors: [],
  stock_total: 5,
} as unknown as ProductDetail;

function renderPage(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('PDP one-click (B8-008)', () => {
  it('does not show stub «Купить в 1 клик» CTA or modal', () => {
    renderPage(<ProductPageClient slug="phone" initialProduct={mockProduct} />);
    expect(screen.queryByText(/Купить в 1 клик/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/заглушка/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Отправить заявку/i })).not.toBeInTheDocument();
  });
});
