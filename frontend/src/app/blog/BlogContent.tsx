'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import Link from 'next/link';
import { Search } from 'lucide-react';
import type { ArticleList, ContentTag } from '@/types';
import type { PaginatedResponse } from '@/types';
import { getArticles } from '@/lib/api/services/content.service';
import { getMediaUrl } from '@/lib/image-url';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { PlaceholderBlock } from '@/components/ui/PlaceholderBlock';
import { cn } from '@/lib/theme/utils';
import { PageContainer } from '@/components/layout/PageContainer';

const CATEGORY_LABELS: Record<string, string> = {
  news: 'Новости',
  guide: 'Гайды',
  review: 'Обзоры',
  other: 'Другое',
};

interface BlogContentProps {
  initialArticles: PaginatedResponse<ArticleList>;
  initialTags: ContentTag[];
}

export function BlogContent({ initialArticles, initialTags }: BlogContentProps) {
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [category, setCategory] = useState<string>('');
  const [tagSlug, setTagSlug] = useState<string>('');
  const [page, setPage] = useState(1);

  const params = useMemo(
    () => ({
      search: search.trim() || undefined,
      category: category || undefined,
      tag: tagSlug || undefined,
      page,
      page_size: 12,
    }),
    [search, category, tagSlug, page]
  );

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['content', 'articles', params],
    queryFn: () => getArticles(params),
    initialData:
      page === 1 && !params.search && !params.category && !params.tag ? initialArticles : undefined,
    placeholderData: prev => prev,
  });

  const articles = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / (params.page_size ?? 12));
  const hasNext = page < totalPages;
  const hasPrev = page > 1;

  const applySearch = () => setSearch(searchInput.trim());

  return (
    <PageContainer className="py-8">
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Блог</h1>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <div className="flex min-w-0 flex-1 gap-2 sm:max-w-xs">
            <Input
              type="search"
              placeholder="Поиск по статьям..."
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applySearch()}
            />
            <Button variant="secondary" size="sm" onClick={applySearch}>
              <Search className="h-4 w-4" />
            </Button>
          </div>
          <select
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            value={category}
            onChange={e => {
              setCategory(e.target.value);
              setPage(1);
            }}
            aria-label="Категория"
          >
            <option value="">Все категории</option>
            {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            value={tagSlug}
            onChange={e => {
              setTagSlug(e.target.value);
              setPage(1);
            }}
            aria-label="Тег"
          >
            <option value="">Все теги</option>
            {initialTags.map(t => (
              <option key={t.id} value={t.slug}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && !data && (
        <div className="flex min-h-[40vh] items-center justify-center">
          <Loading />
        </div>
      )}

      {isError && (
        <Card className="p-6 text-center text-danger">
          Не удалось загрузить статьи. Попробуйте позже.
        </Card>
      )}

      {!isError && articles.length === 0 && (
        <Card className="p-6 text-center text-foreground-muted">
          Статей пока нет или ничего не найдено по заданным фильтрам.
        </Card>
      )}

      {!isError && articles.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {articles.map(article => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!hasPrev || isFetching}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                Назад
              </Button>
              <span className="text-sm text-zinc-600 dark:text-zinc-400">
                Страница {page} из {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasNext || isFetching}
                onClick={() => setPage(p => p + 1)}
              >
                Вперёд
              </Button>
            </div>
          )}
        </>
      )}

      <div className="mt-8 grid gap-4">
        <PlaceholderBlock
          title="Блок: Подписка на блог"
          note="Тут будет форма подписки на новые статьи."
        />
        <PlaceholderBlock
          title="Блок: Популярные материалы"
          note="Тут будет подборка самых читаемых статей."
        />
      </div>
    </PageContainer>
  );
}

function ArticleCard({ article }: { article: ArticleList }) {
  const imageSrc = article.image ? getMediaUrl(article.image) : null;
  const categoryLabel = article.category
    ? (CATEGORY_LABELS[article.category] ?? article.category)
    : null;
  const dateStr = article.published_at
    ? new Date(article.published_at).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    : null;

  return (
    <Link href={`/blog/${article.slug}`}>
      <Card
        variant="interactive"
        className={cn('flex h-full flex-col overflow-hidden p-0 transition-transform')}
      >
        <div className="relative aspect-video w-full shrink-0 bg-zinc-100 dark:bg-zinc-800">
          {imageSrc ? (
            <Image
              src={imageSrc}
              alt=""
              fill
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              className="object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-zinc-400 dark:text-zinc-500">
              Нет изображения
            </div>
          )}
          {categoryLabel && (
            <span className="absolute left-2 top-2 rounded bg-white/90 px-2 py-0.5 text-xs font-medium text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200">
              {categoryLabel}
            </span>
          )}
        </div>
        <div className="flex flex-1 flex-col p-3">
          <h2 className="mb-1 line-clamp-2 font-semibold text-zinc-900 dark:text-zinc-50">
            {article.title}
          </h2>
          {dateStr && <p className="mb-2 text-xs text-foreground-muted">{dateStr}</p>}
          {article.excerpt && (
            <p className="line-clamp-2 flex-1 text-sm text-zinc-600 dark:text-zinc-300">
              {article.excerpt}
            </p>
          )}
          {article.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {article.tags.slice(0, 3).map(t => (
                <span
                  key={t.id}
                  className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300"
                >
                  {t.name}
                </span>
              ))}
            </div>
          )}
        </div>
      </Card>
    </Link>
  );
}
