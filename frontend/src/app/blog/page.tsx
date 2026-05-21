import type { ArticleList, PaginatedResponse } from '@/types';
import { getArticles, getTags } from '@/lib/api/services/content.service';
import { BlogContent } from './BlogContent';

/**
 * Страница блога: SSG — начальные данные подгружаются на этапе сборки (или при первом запросе).
 * generateStaticParams для /blog не требуется (нет динамического сегмента);
 * для /blog/[slug] его можно добавить при реализации страницы статьи.
 */
export default async function BlogPage() {
  let initialArticles: PaginatedResponse<ArticleList> = {
    count: 0,
    next: null,
    previous: null,
    results: [],
  };
  let initialTags: Awaited<ReturnType<typeof getTags>> = [];

  try {
    const [articlesRes, tags] = await Promise.all([
      getArticles({ page: 1, page_size: 12 }),
      getTags(),
    ]);
    initialArticles = articlesRes;
    initialTags = tags;
  } catch {
    // При сборке или при недоступности API показываем пустой список
  }

  return <BlogContent initialArticles={initialArticles} initialTags={initialTags} />;
}
