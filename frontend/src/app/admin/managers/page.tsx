'use client';

import { useState } from 'react';
import Image from 'next/image';
import { useMutation, useQuery } from '@tanstack/react-query';
import { RefreshCw, Trash2 } from 'lucide-react';
import {
  buildManagerFormData,
  createAdminManager,
  deleteAdminManager,
  getAdminManagers,
  updateAdminManager,
  type AdminManagerForm,
  type AdminManagerListItem,
} from '@/lib/api/services/adminManagers.service';
import { getAdminStores } from '@/lib/api/services/adminStores.service';
import { getMediaUrl } from '@/lib/image-url';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';

const emptyForm: AdminManagerForm = {
  name: '',
  slug: '',
  job_title: 'Консультант',
  bio: '',
  store: '',
  is_active: true,
  order: 0,
  photo_alt: '',
  photo_2_alt: '',
};

export default function AdminManagersPage() {
  const [form, setForm] = useState<AdminManagerForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photo2File, setPhoto2File] = useState<File | null>(null);
  const [search, setSearch] = useState('');

  const { data: storesData } = useQuery({
    queryKey: ['admin', 'stores', 'list'],
    queryFn: () => getAdminStores(),
  });
  const stores = storesData?.results ?? [];

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['admin', 'managers', search],
    queryFn: () => getAdminManagers({ search: search || undefined }),
  });

  const managers: AdminManagerListItem[] = data?.results ?? [];

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setPhotoFile(null);
    setPhoto2File(null);
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createAdminManager(
        buildManagerFormData(form, { photo: photoFile, photo_2: photo2File })
      ),
    onSuccess: () => {
      void refetch();
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (id: string) =>
      updateAdminManager(
        id,
        buildManagerFormData(form, { photo: photoFile, photo_2: photo2File })
      ),
    onSuccess: () => {
      void refetch();
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminManager(id),
    onSuccess: () => {
      void refetch();
      resetForm();
    },
  });

  const startEdit = (m: AdminManagerListItem) => {
    setEditingId(m.id);
    setForm({
      name: m.name,
      slug: m.slug,
      job_title: m.job_title || '',
      bio: m.bio || '',
      store: m.store,
      is_active: m.is_active,
      order: m.order,
      photo_alt: m.photo_alt || '',
      photo_2_alt: m.photo_2_alt || '',
    });
    setPhotoFile(null);
    setPhoto2File(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.store) return;
    if (editingId) {
      updateMutation.mutate(editingId);
    } else {
      createMutation.mutate();
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Менеджеры</h1>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Обновить
        </Button>
      </div>

      <Card className="p-6">
        <h2 className="mb-4 text-lg font-semibold text-zinc-900">
          {editingId ? 'Редактировать менеджера' : 'Добавить менеджера'}
        </h2>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-zinc-600">ФИО *</label>
            <Input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Slug (пусто — автогенерация)</label>
            <Input
              value={form.slug ?? ''}
              onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Должность</label>
            <Input
              value={form.job_title ?? ''}
              onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Магазин *</label>
            <select
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={form.store}
              onChange={e => setForm(f => ({ ...f, store: e.target.value }))}
              required
            >
              <option value="">Выберите магазин</option>
              {stores.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.city})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Порядок</label>
            <Input
              type="number"
              value={form.order ?? 0}
              onChange={e => setForm(f => ({ ...f, order: Number(e.target.value) }))}
            />
          </div>
          <div className="flex items-center gap-2 sm:col-span-2">
            <input
              id="manager-active"
              type="checkbox"
              checked={form.is_active ?? true}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
            />
            <label htmlFor="manager-active" className="text-sm text-zinc-700">
              Активен (показывать на сайте)
            </label>
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-zinc-600">О себе</label>
            <textarea
              className="min-h-[80px] w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={form.bio ?? ''}
              onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Фото 1</label>
            <input type="file" accept="image/*" onChange={e => setPhotoFile(e.target.files?.[0] ?? null)} />
          </div>
          <div>
            <label className="mb-1 block text-sm text-zinc-600">Фото 2</label>
            <input type="file" accept="image/*" onChange={e => setPhoto2File(e.target.files?.[0] ?? null)} />
          </div>
          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <Button type="submit" disabled={isSaving}>
              {editingId ? 'Сохранить' : 'Создать'}
            </Button>
            {editingId && (
              <Button type="button" variant="outline" onClick={resetForm}>
                Отмена
              </Button>
            )}
          </div>
        </form>
      </Card>

      <Card className="p-6">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">Список</h2>
          <Input
            placeholder="Поиск по имени"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="max-w-xs"
          />
        </div>
        {isLoading ? (
          <Loading />
        ) : isError ? (
          <p className="text-sm text-red-600">Не удалось загрузить менеджеров.</p>
        ) : managers.length === 0 ? (
          <p className="text-sm text-zinc-500">Менеджеров пока нет.</p>
        ) : (
          <ul className="divide-y divide-zinc-100">
            {managers.map(m => {
              const photoUrl = m.photo ? getMediaUrl(m.photo) : null;
              return (
                <li key={m.id} className="flex flex-wrap items-center gap-4 py-4">
                  <div className="relative size-12 overflow-hidden rounded-full bg-zinc-100">
                    {photoUrl ? (
                      <Image src={photoUrl} alt="" fill className="object-cover" sizes="48px" unoptimized />
                    ) : (
                      <span className="flex size-full items-center justify-center text-sm font-semibold">
                        {m.name.slice(0, 1)}
                      </span>
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-zinc-900">{m.name}</p>
                    <p className="text-sm text-zinc-500">
                      {m.store_name} · /staff/{m.slug}
                      {!m.is_active && ' · скрыт'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => startEdit(m)}>
                      Изменить
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="text-red-600"
                      onClick={() => {
                        if (window.confirm(`Удалить ${m.name}?`)) deleteMutation.mutate(m.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
