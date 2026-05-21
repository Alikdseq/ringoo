import type { NewsList, PaginatedResponse } from '@/types';
import { getNews, getTags } from '@/lib/api/services/content.service';
import { NewsContent } from './NewsContent';

export default async function NewsPage() {
  let initialNews: PaginatedResponse<NewsList> = {
    count: 0,
    next: null,
    previous: null,
    results: [],
  };
  let initialTags: Awaited<ReturnType<typeof getTags>> = [];

  try {
    const [newsRes, tags] = await Promise.all([
      getNews({ page: 1, page_size: 12 }),
      getTags(),
    ]);
    initialNews = newsRes;
    initialTags = tags;
  } catch {
    /* при сборке / недоступном API — пустой список */
  }

  return <NewsContent initialNews={initialNews} initialTags={initialTags} />;
}
