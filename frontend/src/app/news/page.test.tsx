import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import NewsPage from './page';
import { NewsContent } from './NewsContent';

vi.mock('@/lib/api/services/content.service', () => ({
  getNews: vi.fn(),
  getTags: vi.fn(),
}));

const mockGetNews = vi.mocked((await import('@/lib/api/services/content.service')).getNews);
const mockGetTags = vi.mocked((await import('@/lib/api/services/content.service')).getTags);

const defaultNews = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 'n1',
      title: 'Запуск доставки',
      slug: 'delivery-launch',
      excerpt: 'Расширяем зоны доставки.',
      image: null,
      category: 'company',
      tags: [] as { id: string; name: string; slug: string }[],
      is_featured: true,
      published_at: '2024-02-01T10:00:00Z',
      views_count: 3,
      created_at: '2024-01-20T00:00:00Z',
    },
  ],
};

const defaultTags = [{ id: 't1', name: 'Сервис', slug: 'service' }];

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('NewsPage', () => {
  beforeEach(() => {
    mockGetNews.mockResolvedValue(defaultNews);
    mockGetTags.mockResolvedValue(defaultTags);
  });

  it('renders news list from server', async () => {
    const page = await NewsPage();
    renderWithClient(page);

    expect(screen.getByRole('heading', { name: 'Новости' })).toBeInTheDocument();
    expect(screen.getByText('Запуск доставки')).toBeInTheDocument();
  });
});

describe('NewsContent', () => {
  it('links to news slug', () => {
    renderWithClient(<NewsContent initialNews={defaultNews} initialTags={defaultTags} />);

    const link = screen.getByRole('link', { name: /Запуск доставки/ });
    expect(link).toHaveAttribute('href', '/news/delivery-launch');
  });
});
