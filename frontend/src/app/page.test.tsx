import { render, screen } from '@testing-library/react';
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
  return {
    ...actual,
    getProducts: vi.fn().mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    }),
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

function renderHome() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <UiModeProvider initialMode="official">
        <Home />
      </UiModeProvider>
    </QueryClientProvider>
  );
}

describe('Home', () => {
  it('renders hero heading and CTA to catalog', () => {
    renderHome();
    expect(screen.getByRole('heading', { name: /электроника с доставкой/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^в каталог$/i })).toHaveAttribute('href', '/catalog');
  });

  it('renders popular now section heading', () => {
    renderHome();
    expect(screen.getByRole('heading', { name: /популярное сейчас/i })).toBeInTheDocument();
  });

  it('renders bottom CTA link to catalog', () => {
    renderHome();
    expect(screen.getByRole('link', { name: /больше в каталоге/i })).toHaveAttribute(
      'href',
      '/catalog'
    );
  });
});
