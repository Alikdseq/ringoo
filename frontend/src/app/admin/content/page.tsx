'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import {
  getAdminArticles,
  getAdminNews,
  getAdminReviews,
  updateAdminReviewApproval,
  createAdminArticle,
  deleteAdminArticle,
  createAdminNews,
  deleteAdminNews,
  type AdminArticleListItem,
  type AdminNewsListItem,
  type AdminReviewListItem,
  type AdminArticlePayload,
  type AdminNewsPayload,
} from '@/lib/api/services/adminContent.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

import {
  createAdminPageGallery,
  deleteAdminPageGallery,
  getAdminPageGallery,
  type PageGalleryPlacement,
} from '@/lib/api/services/pageGallery.service';

type TabKey = 'articles' | 'news' | 'reviews' | 'gallery';

export default function AdminContentPage() {
  const [tab, setTab] = useState<TabKey>('articles');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Контент</h1>
      </div>

      <div className="flex gap-2 border-b border-zinc-200">
        <TabButton active={tab === 'articles'} onClick={() => setTab('articles')} label="Статьи" />
        <TabButton active={tab === 'news'} onClick={() => setTab('news')} label="Новости" />
        <TabButton active={tab === 'reviews'} onClick={() => setTab('reviews')} label="Отзывы" />
        <TabButton active={tab === 'gallery'} onClick={() => setTab('gallery')} label="Галереи страниц" />
      </div>

      {tab === 'articles' && <ArticlesTab />}
      {tab === 'news' && <NewsTab />}
      {tab === 'reviews' && <ReviewsTab />}
      {tab === 'gallery' && <GalleryTab />}
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  label: string;
  onClick: () => void;
}

function TabButton({ active, label, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`border-b-2 px-3 py-2 text-sm font-medium ${
        active
          ? 'border-[var(--color-brand)] text-zinc-900'
          : 'border-transparent text-zinc-500 hover:text-zinc-800'
      }`}
    >
      {label}
    </button>
  );
}

function ArticlesTab() {
  const [page, setPage] = useState(1);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [form, setForm] = useState<AdminArticlePayload>({
    title: '',
    slug: '',
    content: '',
    excerpt: '',
    category: '',
    is_published: false,
    published_at: '',
    tags: [],
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'content', 'articles', { page }],
    queryFn: () => getAdminArticles({ page }),
  });

  const createMutation = useMutation({
    mutationFn: (variables: { payload: AdminArticlePayload; image: File | null }) =>
      createAdminArticle(variables.payload, variables.image),
    onSuccess: () => {
      void refetch();
      setForm({
        title: '',
        slug: '',
        content: '',
        excerpt: '',
        category: '',
        is_published: false,
        published_at: '',
        tags: [],
      });
      setImageFile(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminArticle(id),
    onSuccess: () => {
      void refetch();
    },
  });

  const articles: AdminArticleListItem[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = articles.length > 0 ? articles.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.slug.trim() || !form.content.trim()) return;
    createMutation.mutate({ payload: form, image: imageFile });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-900">Статьи</h2>
        <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Обновить
        </Button>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить статьи.</div>
        ) : articles.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Статьи ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[700px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Заголовок</th>
                  <th className="px-3 py-2 text-left">Slug</th>
                  <th className="px-3 py-2 text-left">Категория</th>
                  <th className="px-3 py-2 text-left">Опубликована</th>
                  <th className="px-3 py-2 text-left">Дата публикации</th>
                  <th className="px-3 py-2 text-left">Создана</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {articles.map(article => {
                  const publishedAt = article.published_at ? new Date(article.published_at) : null;
                  const createdAt = new Date(article.created_at);
                  return (
                    <tr key={article.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{article.title}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{article.slug}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{article.category || '—'}</td>
                      <td className="px-3 py-2 text-xs">
                        {article.is_published ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Да
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Нет
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {publishedAt && !Number.isNaN(publishedAt.getTime())
                          ? publishedAt.toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {!Number.isNaN(createdAt.getTime()) ? createdAt.toLocaleString() : ''}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="text-red-600 hover:underline"
                          onClick={() => deleteMutation.mutate(article.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-zinc-600">
          <div>
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              Назад
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Новая статья</h3>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Заголовок</label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm({ ...form, title: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Slug</label>
              <input
                type="text"
                value={form.slug}
                onChange={e => setForm({ ...form, slug: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Краткое описание</label>
            <textarea
              value={form.excerpt ?? ''}
              onChange={e => setForm({ ...form, excerpt: e.target.value })}
              className="min-h-[60px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Контент (HTML/текст)</label>
            <textarea
              value={form.content}
              onChange={e => setForm({ ...form, content: e.target.value })}
              className="min-h-[120px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              required
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Категория</label>
              <input
                type="text"
                value={form.category ?? ''}
                onChange={e => setForm({ ...form, category: e.target.value || '' })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                placeholder="news, guide, review..."
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата публикации</label>
              <input
                type="datetime-local"
                value={form.published_at ?? ''}
                onChange={e => setForm({ ...form, published_at: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_published ?? false}
                  onChange={e => setForm({ ...form, is_published: e.target.checked })}
                />
                Опубликована
              </label>
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Изображение</label>
            <input
              type="file"
              accept="image/*"
              onChange={e => {
                const file = e.target.files?.[0] ?? null;
                setImageFile(file);
              }}
              className="block text-sm"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={createMutation.isPending}>
              Создать статью
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function NewsTab() {
  const [page, setPage] = useState(1);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [form, setForm] = useState<AdminNewsPayload>({
    title: '',
    slug: '',
    content: '',
    excerpt: '',
    category: '',
    is_published: false,
    is_featured: false,
    published_at: '',
    tags: [],
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'content', 'news', { page }],
    queryFn: () => getAdminNews({ page }),
  });

  const createMutation = useMutation({
    mutationFn: (variables: { payload: AdminNewsPayload; image: File | null }) =>
      createAdminNews(variables.payload, variables.image),
    onSuccess: () => {
      void refetch();
      setForm({
        title: '',
        slug: '',
        content: '',
        excerpt: '',
        category: '',
        is_published: false,
        is_featured: false,
        published_at: '',
        tags: [],
      });
      setImageFile(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminNews(id),
    onSuccess: () => {
      void refetch();
    },
  });

  const items: AdminNewsListItem[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = items.length > 0 ? items.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.slug.trim() || !form.content.trim()) return;
    createMutation.mutate({ payload: form, image: imageFile });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-900">Новости</h2>
        <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Обновить
        </Button>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить новости.</div>
        ) : items.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Новости ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[700px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Заголовок</th>
                  <th className="px-3 py-2 text-left">Slug</th>
                  <th className="px-3 py-2 text-left">Категория</th>
                  <th className="px-3 py-2 text-left">Опубликована</th>
                  <th className="px-3 py-2 text-left">Витрина</th>
                  <th className="px-3 py-2 text-left">Дата публикации</th>
                  <th className="px-3 py-2 text-left">Создана</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => {
                  const publishedAt = item.published_at ? new Date(item.published_at) : null;
                  const createdAt = new Date(item.created_at);
                  return (
                    <tr key={item.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{item.title}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{item.slug}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{item.category || '—'}</td>
                      <td className="px-3 py-2 text-xs">
                        {item.is_published ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Да
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Нет
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {item.is_featured ? (
                          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-amber-700">
                            На главной
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {publishedAt && !Number.isNaN(publishedAt.getTime())
                          ? publishedAt.toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {!Number.isNaN(createdAt.getTime()) ? createdAt.toLocaleString() : ''}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="text-red-600 hover:underline"
                          onClick={() => deleteMutation.mutate(item.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Удалить
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-zinc-600">
          <div>
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              Назад
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}

      <Card className="space-y-3 p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Новая новость</h3>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Заголовок</label>
              <input
                type="text"
                value={form.title}
                onChange={e => setForm({ ...form, title: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Slug</label>
              <input
                type="text"
                value={form.slug}
                onChange={e => setForm({ ...form, slug: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Краткое описание</label>
            <textarea
              value={form.excerpt ?? ''}
              onChange={e => setForm({ ...form, excerpt: e.target.value })}
              className="min-h-[60px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Контент</label>
            <textarea
              value={form.content}
              onChange={e => setForm({ ...form, content: e.target.value })}
              className="min-h-[120px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              required
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Категория</label>
              <input
                type="text"
                value={form.category ?? ''}
                onChange={e => setForm({ ...form, category: e.target.value || '' })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                placeholder="news, guide, review..."
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата публикации</label>
              <input
                type="datetime-local"
                value={form.published_at ?? ''}
                onChange={e => setForm({ ...form, published_at: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_published ?? false}
                  onChange={e => setForm({ ...form, is_published: e.target.checked })}
                />
                Опубликована
              </label>
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_featured ?? false}
                  onChange={e => setForm({ ...form, is_featured: e.target.checked })}
                />
                На главной
              </label>
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Изображение</label>
            <input
              type="file"
              accept="image/*"
              onChange={e => {
                const file = e.target.files?.[0] ?? null;
                setImageFile(file);
              }}
              className="block text-sm"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={createMutation.isPending}>
              Создать новость
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function ReviewsTab() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<'all' | 'approved' | 'pending'>('all');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'content', 'reviews', { page, statusFilter }],
    queryFn: () =>
      getAdminReviews({
        page,
        is_approved:
          statusFilter === 'all' ? undefined : statusFilter === 'approved' ? 'true' : 'false',
      }),
  });

  const approveMutation = useMutation({
    mutationFn: (review: AdminReviewListItem) =>
      updateAdminReviewApproval(review.id, !review.is_approved),
    onSuccess: () => {
      void refetch();
    },
  });

  const items: AdminReviewListItem[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = items.length > 0 ? items.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-semibold text-zinc-900">Отзывы</h2>
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as 'all' | 'approved' | 'pending')}
            className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
          >
            <option value="all">Все</option>
            <option value="approved">Одобренные</option>
            <option value="pending">На модерации</option>
          </select>
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить отзывы.</div>
        ) : items.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Отзывы по текущему фильтру не найдены.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Автор</th>
                  <th className="px-3 py-2 text-left">Рейтинг</th>
                  <th className="px-3 py-2 text-left">Текст</th>
                  <th className="px-3 py-2 text-left">Статус</th>
                  <th className="px-3 py-2 text-left">Дата</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.map(review => {
                  const createdAt = new Date(review.created_at);
                  const created = !Number.isNaN(createdAt.getTime())
                    ? createdAt.toLocaleString()
                    : '';
                  return (
                    <tr key={review.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{review.name}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{review.rating}</td>
                      <td className="px-3 py-2 text-xs text-zinc-700">{review.comment}</td>
                      <td className="px-3 py-2 text-xs">
                        {review.is_approved ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Одобрен
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            На модерации
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{created}</td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="text-[var(--color-brand)] hover:underline"
                          onClick={() => approveMutation.mutate(review)}
                          disabled={approveMutation.isPending}
                        >
                          {review.is_approved ? 'Отклонить' : 'Одобрить'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-zinc-600">
          <div>
            Страница {page} из {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              Назад
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function GalleryTab() {
  const [placement, setPlacement] = useState<PageGalleryPlacement>('stores_hero');
  const [file, setFile] = useState<File | null>(null);
  const [altText, setAltText] = useState('');
  const [sortOrder, setSortOrder] = useState(0);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'page-gallery', placement],
    queryFn: () => getAdminPageGallery(placement),
  });

  const items = data?.results ?? [];

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Выберите файл');
      const fd = new FormData();
      fd.append('placement', placement);
      fd.append('image', file);
      fd.append('alt_text', altText);
      fd.append('sort_order', String(sortOrder));
      fd.append('is_active', 'true');
      return createAdminPageGallery(fd);
    },
    onSuccess: () => {
      void refetch();
      setFile(null);
      setAltText('');
      setSortOrder(0);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminPageGallery(id),
    onSuccess: () => void refetch(),
  });

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="mb-4 text-lg font-semibold text-zinc-900">Добавить фото</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Страница</label>
            <select
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={placement}
              onChange={e => setPlacement(e.target.value as PageGalleryPlacement)}
            >
              <option value="stores_hero">Магазины — hero</option>
              <option value="about_hero">О нас — hero</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Порядок</label>
            <input
              type="number"
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={sortOrder}
              onChange={e => setSortOrder(Number(e.target.value))}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-zinc-600">Alt-текст</label>
            <input
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={altText}
              onChange={e => setAltText(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-zinc-600">Изображение *</label>
            <input type="file" accept="image/*" onChange={e => setFile(e.target.files?.[0] ?? null)} />
          </div>
          <Button
            type="button"
            disabled={!file || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            Загрузить
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">Загруженные ({placement})</h2>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        {isLoading ? (
          <Loading />
        ) : items.length === 0 ? (
          <p className="text-sm text-zinc-500">Нет изображений для этой страницы.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map(item => (
              <li key={item.id} className="rounded-xl border border-zinc-200 p-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.image}
                  alt={item.alt_text}
                  className="mb-2 aspect-[4/3] w-full rounded-lg object-cover"
                />
                <p className="text-xs text-zinc-500">Порядок: {item.sort_order}</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-2 text-red-600"
                  onClick={() => {
                    if (window.confirm('Удалить изображение?')) deleteMutation.mutate(item.id);
                  }}
                >
                  Удалить
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
