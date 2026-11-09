'use client';

import { Fragment, useMemo, useState, type ReactElement } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  getAdminCategories,
  type AdminCategory,
  updateAdminCategory,
  type CategoryPayload,
} from '@/lib/api/services/adminCatalog.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

const emptyForm: CategoryPayload = {
  title: '',
  slug: '',
  parent: null,
  description: '',
  sort_order: 0,
  is_active: true,
  meta_title: '',
  meta_description: '',
};

export default function AdminCategoriesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CategoryPayload>(emptyForm);
  const [imageFile, setImageFile] = useState<File | null>(null);

  const {
    data: categories = [],
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['admin', 'categories'],
    queryFn: getAdminCategories,
  });

  const categoriesByParent = useMemo(() => {
    const roots: AdminCategory[] = [];
    const children: Record<string, AdminCategory[]> = {};
    for (const c of categories) {
      if (!c.parent) {
        roots.push(c);
      } else {
        children[c.parent] = children[c.parent] || [];
        children[c.parent].push(c);
      }
    }
    const sortFn = (a: AdminCategory, b: AdminCategory) =>
      a.sort_order - b.sort_order || a.title.localeCompare(b.title);
    roots.sort(sortFn);
    Object.values(children).forEach(arr => arr.sort(sortFn));
    return { roots, children, sortFn };
  }, [categories]);

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      payload,
      image,
    }: {
      id: string;
      payload: CategoryPayload;
      image: File | null;
    }) => updateAdminCategory(id, payload, image),
    onSuccess: () => {
      void refetch();
    },
  });

  const handleSelect = (cat: AdminCategory) => {
    setSelectedId(cat.id);
    setForm({
      title: cat.title,
      slug: cat.slug,
      parent: cat.parent,
      description: cat.description ?? '',
      sort_order: cat.sort_order,
      is_active: cat.is_active,
      meta_title: cat.meta_title ?? '',
      meta_description: cat.meta_description ?? '',
    });
    setImageFile(null);
  };

  const handleNew = () => {
    setSelectedId(null);
    setForm(emptyForm);
    setImageFile(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) return;
    updateMutation.mutate({ id: selectedId, payload: form, image: imageFile });
  };

  const renderRow = (cat: AdminCategory, level: number = 0): ReactElement => {
    const { children } = categoriesByParent;
    return (
      <Fragment key={cat.id}>
        <tr
          className={`cursor-pointer border-b border-zinc-100 hover:bg-zinc-50 ${
            selectedId === cat.id ? 'bg-zinc-50' : ''
          }`}
          onClick={() => handleSelect(cat)}
        >
          <td className="px-3 py-2 text-sm text-zinc-900">
            <span style={{ paddingLeft: level * 16 }}>{cat.title}</span>
          </td>
          <td className="px-3 py-2 font-mono text-xs text-zinc-500">{cat.onec_code || '—'}</td>
          <td className="px-3 py-2 text-xs text-zinc-500">{cat.slug}</td>
          <td className="px-3 py-2 text-xs text-zinc-500">
            {cat.parent ? (categories.find(c => c.id === cat.parent)?.title ?? '—') : 'Корень'}
          </td>
          <td className="px-3 py-2 text-xs text-zinc-500">{cat.sort_order}</td>
          <td className="px-3 py-2 text-xs">
            {cat.is_active ? (
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                Активна
              </span>
            ) : (
              <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">Выключена</span>
            )}
          </td>
          <td className="px-3 py-2 text-right text-xs" onClick={e => e.stopPropagation()}>
            <button
              type="button"
              className="text-[var(--color-brand)] hover:underline"
              onClick={() => {
                updateMutation.mutate({
                  id: cat.id,
                  payload: {
                    title: cat.title,
                    slug: cat.slug,
                    parent: cat.parent,
                    description: cat.description ?? '',
                    sort_order: cat.sort_order,
                    is_active: !cat.is_active,
                    meta_title: cat.meta_title ?? '',
                    meta_description: cat.meta_description ?? '',
                  },
                  image: null,
                });
              }}
            >
              {cat.is_active ? 'Скрыть на сайте' : 'Показать на сайте'}
            </button>
          </td>
        </tr>
        {(children[cat.id] || []).map(child => renderRow(child, level + 1))}
      </Fragment>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Категории</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Иерархия папок приходит из 1С (код папки). Локально можно править SEO, описание, видимость
            на сайте.
          </p>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            Обновить
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[2fr,1.4fr]">
        <Card className="overflow-hidden">
          {isLoading ? (
            <div className="flex min-h-[260px] items-center justify-center">
              <Loading />
            </div>
          ) : isError ? (
            <div className="p-4 text-sm text-red-600">Не удалось загрузить категории.</div>
          ) : categories.length === 0 ? (
            <div className="p-4 text-sm text-zinc-500">Категории ещё не созданы.</div>
          ) : (
            <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
              <table className="w-full min-w-[700px] text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                    <th className="px-3 py-2 text-left">Название</th>
                    <th className="px-3 py-2 text-left">Код 1С</th>
                    <th className="px-3 py-2 text-left">Slug</th>
                    <th className="px-3 py-2 text-left">Родитель</th>
                    <th className="px-3 py-2 text-left">Порядок</th>
                    <th className="px-3 py-2 text-left">Статус</th>
                    <th className="px-3 py-2 text-right">Действия</th>
                  </tr>
                </thead>
                <tbody>{categoriesByParent.roots.map(cat => renderRow(cat, 0))}</tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="p-4">
          <h2 className="mb-3 text-sm font-semibold text-zinc-900">
            {selectedId ? 'Локальные настройки категории' : 'Выберите категорию в дереве'}
          </h2>
          {!selectedId ? (
            <p className="text-sm text-zinc-500">
              Создание и удаление категорий выполняется синхронизацией из 1С. Здесь — только
              витринные поля Ringoo.
            </p>
          ) : (
          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Название (из 1С)</label>
              <input
                type="text"
                value={form.title}
                readOnly
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Slug</label>
              <input
                type="text"
                value={form.slug}
                readOnly
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Код 1С</label>
              <input
                type="text"
                value={
                  categories.find(c => c.id === selectedId)?.onec_code || '—'
                }
                readOnly
                className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 font-mono text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Описание</label>
              <textarea
                value={form.description ?? ''}
                onChange={e => setForm({ ...form, description: e.target.value })}
                rows={3}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">
                  Порядок сортировки
                </label>
                <input
                  type="number"
                  value={form.sort_order ?? 0}
                  onChange={e =>
                    setForm({
                      ...form,
                      sort_order: Number(e.target.value) || 0,
                    })
                  }
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">Статус</label>
                <select
                  value={form.is_active ? 'true' : 'false'}
                  onChange={e => setForm({ ...form, is_active: e.target.value === 'true' })}
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                >
                  <option value="true">Активна</option>
                  <option value="false">Выключена</option>
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Meta title (SEO)</label>
              <input
                type="text"
                value={form.meta_title ?? ''}
                onChange={e => setForm({ ...form, meta_title: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">
                Meta description (SEO)
              </label>
              <textarea
                value={form.meta_description ?? ''}
                onChange={e => setForm({ ...form, meta_description: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">
                Изображение категории
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={e => setImageFile(e.target.files ? (e.target.files[0] ?? null) : null)}
                className="block w-full text-xs text-zinc-500"
              />
              {selectedId && (
                <p className="text-xs text-zinc-400">
                  Текущее изображение можно посмотреть на витрине; здесь загружается новое при
                  необходимости.
                </p>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" size="sm" onClick={handleNew}>
                Снять выбор
              </Button>
              <Button
                type="submit"
                size="sm"
                loading={updateMutation.isPending}
              >
                Сохранить локальные поля
              </Button>
            </div>
          </form>
          )}
        </Card>
      </div>
    </div>
  );
}
