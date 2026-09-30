import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { useProducts, useProduct, useCategories } from './useProducts';
import { renderWithProviders } from '@/test/helpers';
import { mockPaginatedProducts, mockProductDetail, mockCategory } from '@/test/mocks/api';
import { getProducts, getProductDetail, getCategories } from '@/lib/api/services/products.service';

vi.mock('@/lib/api/services/products.service', () => ({
  getProducts: vi.fn(),
  getProductDetail: vi.fn(),
  getCategories: vi.fn(),
}));

function UseProductsConsumer({ filters }: { filters: { page?: number } }) {
  const { data, isSuccess, isLoading } = useProducts(filters);
  if (isLoading) return <span>Loading products</span>;
  if (isSuccess && data?.pages?.[0]?.results?.length)
    return <span>Products: {data.pages[0].results[0].title}</span>;
  return <span>No data</span>;
}

function UseProductConsumer({ slug }: { slug: string }) {
  const { data, isSuccess, isLoading } = useProduct(slug);
  if (isLoading) return <span>Loading product</span>;
  if (isSuccess && data) return <span>Product: {data.title}</span>;
  return <span>No data</span>;
}

function UseCategoriesConsumer() {
  const { data, isSuccess, isLoading } = useCategories();
  if (isLoading) return <span>Loading categories</span>;
  if (isSuccess && data?.length) return <span>Categories: {data[0].title}</span>;
  return <span>No data</span>;
}

describe('useProducts', () => {
  beforeEach(() => {
    vi.mocked(getProducts).mockResolvedValue(mockPaginatedProducts);
  });

  it('fetches products and returns first page', async () => {
    renderWithProviders(<UseProductsConsumer filters={{}} />);
    expect(screen.getByText('Loading products')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Products: Тестовый товар/)).toBeInTheDocument();
    });
    expect(getProducts).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
  });
});

describe('useProduct', () => {
  beforeEach(() => {
    vi.mocked(getProductDetail).mockResolvedValue(mockProductDetail);
  });

  it('fetches product by slug', async () => {
    renderWithProviders(<UseProductConsumer slug="test-product" />);
    expect(screen.getByText('Loading product')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Product: Тестовый товар/)).toBeInTheDocument();
    });
    expect(getProductDetail).toHaveBeenCalledWith('test-product');
  });
});

describe('useCategories', () => {
  beforeEach(() => {
    vi.mocked(getCategories).mockResolvedValue([mockCategory]);
  });

  it('fetches categories', async () => {
    renderWithProviders(<UseCategoriesConsumer />);
    expect(screen.getByText('Loading categories')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Categories: Категория/)).toBeInTheDocument();
    });
    expect(getCategories).toHaveBeenCalled();
  });
});
