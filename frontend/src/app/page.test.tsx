import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UiModeProvider } from '@/lib/providers/UiModeProvider';
import Home from './page';

vi.mock('@/lib/utils/canUse3D', () => ({
  useCanUse3D: () => false,
}));

vi.mock('@/lib/hooks/useProducts', () => ({
  useCategories: () => ({ data: [], isLoading: false, isError: false }),
}));

vi.mock('@/lib/api/services/products.service', async importOriginal => {
  const actual = await importOriginal<typeof import('@/lib/api/services/products.service')>();
  const emptyPage = { count: 0, next: null, previous: null, results: [] };
  return {
    ...actual,
    fetchProductsServer: vi.fn().mockResolvedValue(emptyPage),
    getProducts: vi.fn().mockResolvedValue(emptyPage),
  };
});

vi.mock('@/lib/api/services/promotions.service', () => ({
  getPromotions: vi.fn().mockResolvedValue([]),
}));

vi.mock('@/lib/api/services/stores.service', () => ({
  getStores: vi.fn().mockResolvedValue({
    count: 0,
    next: null,
    previous: null,
    results: [],
  }),
}));

vi.mock('next/dynamic', () => ({
  default: () => {
    const Stub = () => null;
    return Stub;
  },
}));

async function renderHome() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const page = await Home();
  render(
    <QueryClientProvider client={client}>
      <UiModeProvider initialMode="official">{page}</UiModeProvider>
    </QueryClientProvider>
  );
}

describe('Home', () => {
  it('renders promo section heading', async () => {
    await renderHome();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /акции дня/i })).toBeInTheDocument();
    });
  });

  it('renders popular now section heading', async () => {
    await renderHome();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /популярное сейчас/i })).toBeInTheDocument();
    });
  });

  it('renders link to catalog from popular section', async () => {
    await renderHome();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /больше в каталоге/i })).toHaveAttribute(
        'href',
        '/catalog'
      );
    });
  });
});
