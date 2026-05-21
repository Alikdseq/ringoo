import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import BlogPage from './page';
import { BlogContent } from './BlogContent';

vi.mock('@/lib/api/services/content.service', () => ({
  getArticles: vi.fn(),
  getTags: vi.fn(),
}));

const mockGetArticles = vi.mocked((await import('@/lib/api/services/content.service')).getArticles);
const mockGetTags = vi.mocked((await import('@/lib/api/services/content.service')).getTags);

const defaultArticles = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 'a1',
      title: 'Первая статья',
      slug: 'first-article',
      excerpt: 'Краткое описание первой статьи.',
      image: null,
      category: 'guide',
      tags: [{ id: 't1', name: 'Гайд', slug: 'guide' }],
      published_at: '2024-01-15T10:00:00Z',
      views_count: 10,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'a2',
      title: 'Вторая статья',
      slug: 'second-article',
      excerpt: 'Краткое описание второй статьи.',
      image: null,
      category: 'news',
      tags: [],
      published_at: '2024-01-10T10:00:00Z',
      views_count: 5,
      created_at: '2024-01-05T00:00:00Z',
    },
  ],
};

const defaultTags = [
  { id: 't1', name: 'Гайд', slug: 'guide' },
  { id: 't2', name: 'Новости', slug: 'news' },
];

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe('BlogPage', () => {
  beforeEach(() => {
    mockGetArticles.mockResolvedValue(defaultArticles);
    mockGetTags.mockResolvedValue(defaultTags);
  });

  it('renders blog with initial articles from server', async () => {
    const page = await BlogPage();
    renderWithClient(page);

    expect(screen.getByText('Блог')).toBeInTheDocument();
    expect(screen.getByText('Первая статья')).toBeInTheDocument();
    expect(screen.getByText('Вторая статья')).toBeInTheDocument();
  });
});

describe('BlogContent', () => {
  it('renders grid of articles and filters', () => {
    renderWithClient(<BlogContent initialArticles={defaultArticles} initialTags={defaultTags} />);

    expect(screen.getByText('Блог')).toBeInTheDocument();
    expect(screen.getByText('Первая статья')).toBeInTheDocument();
    expect(screen.getByText('Вторая статья')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Поиск по статьям...')).toBeInTheDocument();
    expect(screen.getByLabelText('Категория')).toBeInTheDocument();
    expect(screen.getByLabelText('Тег')).toBeInTheDocument();
  });

  it('links article cards to blog slug', () => {
    renderWithClient(<BlogContent initialArticles={defaultArticles} initialTags={defaultTags} />);

    const link1 = screen.getByRole('link', { name: /Первая статья/ });
    expect(link1).toHaveAttribute('href', '/blog/first-article');
    const link2 = screen.getByRole('link', { name: /Вторая статья/ });
    expect(link2).toHaveAttribute('href', '/blog/second-article');
  });

  it('shows empty state when no articles', () => {
    renderWithClient(
      <BlogContent
        initialArticles={{ count: 0, next: null, previous: null, results: [] }}
        initialTags={[]}
      />
    );

    expect(screen.getByText(/Статей пока нет или ничего не найдено/)).toBeInTheDocument();
  });
});
