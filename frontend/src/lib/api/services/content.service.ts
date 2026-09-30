import { apiClient } from '@/lib/api/client';
import type { ArticleList, ContentTag, NewsList, PaginatedResponse } from '@/types';

export interface ArticlesParams {
  search?: string;
  category?: string;
  tag?: string;
  page?: number;
  page_size?: number;
}

export async function getArticles(
  params: ArticlesParams = {}
): Promise<PaginatedResponse<ArticleList>> {
  const { data } = await apiClient.get<PaginatedResponse<ArticleList>>('/content/articles/', {
    params,
  });
  return data;
}

export interface NewsParams {
  search?: string;
  category?: string;
  tag?: string;
  /** Соответствует `?is_featured=true` в API */
  is_featured?: boolean;
  page?: number;
  page_size?: number;
}

export async function getNews(params: NewsParams = {}): Promise<PaginatedResponse<NewsList>> {
  const { data } = await apiClient.get<PaginatedResponse<NewsList>>('/content/news/', {
    params,
  });
  return data;
}

export async function getTags(): Promise<ContentTag[]> {
  const { data } = await apiClient.get<ContentTag[]>('/content/tags/');
  return Array.isArray(data) ? data : [];
}
