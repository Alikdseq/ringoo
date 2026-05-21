import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PromotionsPage from './page';

// JSDOM: polyfill for code that checks prefers-reduced-motion etc.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

vi.mock('@/lib/api/services/promotions.service', () => ({
  getPromotions: vi.fn(),
}));

vi.mock('@/lib/api/services/products.service', () => ({
  getProducts: vi.fn(),
}));

vi.mock('@/lib/hooks/useProducts', () => ({
  useCategories: vi.fn(() => ({ data: [] })),
}));

const mockGetPromotions = vi.mocked(
  (await import('@/lib/api/services/promotions.service')).getPromotions
);
const mockGetProducts = vi.mocked((await import('@/lib/api/services/products.service')).getProducts);

const futureEnd = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
const mockPromotions = [
  {
    id: 'p1',
    title: 'Скидка 10%',
    description: 'На все товары категории Электроника',
    image: null,
    discount_type: 'percent' as const,
    discount_value: '10.00',
    start_date: new Date(Date.now() - 86400000).toISOString(),
    end_date: futureEnd,
    category_slugs: ['electronics'],
    created_at: new Date().toISOString(),
  },
];

const mockProducts = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 'prod1',
      title: 'Товар со скидкой',
      slug: 'discounted',
      price: '9000',
      old_price: '10000',
      rating: 4.6,
      reviews_count: 10,
      category: { id: 'c1', title: 'Электроника', slug: 'electronics', parent: null, description: null },
      discount_percent: 10,
      availability_status: 'in_stock' as const,
    },
  ],
};

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('PromotionsPage', () => {
  beforeEach(() => {
    mockGetPromotions.mockResolvedValue(mockPromotions);
    mockGetProducts.mockResolvedValue(mockProducts as any);
  });

  it('renders hero and filters', async () => {
    renderWithClient(<PromotionsPage />);

    expect(
      screen.getByText('Экономить — это умно. А у нас ещё и выгодно.')
    ).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Все акции' }).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Скидка %' })).toBeInTheDocument();
  });

  it('renders list of promotions with discount and timer', async () => {
    renderWithClient(<PromotionsPage />);

    expect((await screen.findAllByText('Скидка 10%')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('На все товары категории Электроника').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/До конца:/).length).toBeGreaterThan(0);
  });

  it('shows empty state when no promotions', async () => {
    mockGetPromotions.mockResolvedValue([]);
    mockGetProducts.mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    } as any);

    renderWithClient(<PromotionsPage />);

    expect(await screen.findByText('Сейчас нет активных акций.')).toBeInTheDocument();
  });
});
