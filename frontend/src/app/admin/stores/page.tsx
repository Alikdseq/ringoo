'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import Image from 'next/image';
import { RefreshCw } from 'lucide-react';
import {
  getAdminStores,
  createAdminStore,
  updateAdminStore,
  deleteAdminStore,
  getAdminStoreImages,
  uploadAdminStoreImage,
  deleteAdminStoreImage,
  type AdminStoreListItem,
  type AdminStorePayload,
} from '@/lib/api/services/adminStores.service';
import { getMediaUrl } from '@/lib/image-url';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

export default function AdminStoresPage() {
  const [form, setForm] = useState<AdminStorePayload>({
    name: '',
    slug: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    latitude: '',
    longitude: '',
    working_hours: {},
    is_active: true,
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'stores', 'list'],
    queryFn: () => getAdminStores(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminStorePayload) => createAdminStore(payload),
    onSuccess: () => {
      void refetch();
      setForm({
        name: '',
        slug: '',
        address: '',
        city: '',
        phone: '',
        email: '',
        latitude: '',
        longitude: '',
        working_hours: {},
        is_active: true,
      });
      setEditingId(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (variables: { id: string; payload: Partial<AdminStorePayload> }) =>
      updateAdminStore(variables.id, variables.payload),
    onSuccess: () => {
      void refetch();
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminStore(id),
    onSuccess: () => {
      void refetch();
      setEditingId(null);
    },
  });

  const {
    data: storeImages = [],
    refetch: refetchStoreImages,
  } = useQuery({
    queryKey: ['admin', 'store-images', editingId],
    queryFn: () => getAdminStoreImages(editingId!),
    enabled: !!editingId,
  });

  const uploadImageMutation = useMutation({
    mutationFn: (file: File) => uploadAdminStoreImage(editingId!, file),
    onSuccess: () => void refetchStoreImages(),
  });

  const deleteImageMutation = useMutation({
    mutationFn: (id: string) => deleteAdminStoreImage(id),
    onSuccess: () => void refetchStoreImages(),
  });

  const stores: AdminStoreListItem[] = data?.results ?? [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.slug.trim() || !form.address.trim() || !form.city.trim()) {
      return;
    }
    const payload: AdminStorePayload = {
      ...form,
      phone: form.phone || null,
      email: form.email || null,
      latitude: form.latitude || null,
      longitude: form.longitude || null,
      working_hours:
        form.working_hours && Object.keys(form.working_hours).length > 0 ? form.working_hours : {},
      is_active: form.is_active ?? true,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (store: AdminStoreListItem) => {
    setEditingId(store.id);
    setForm({
      name: store.name,
      slug: store.slug,
      address: store.address,
      city: store.city,
      phone: store.phone ?? '',
      email: store.email ?? '',
      latitude: store.latitude ?? '',
      longitude: store.longitude ?? '',
      working_hours: store.working_hours ?? {},
      is_active: store.is_active,
    });
  };

  const handleWorkingHoursChange = (value: string) => {
    try {
      const parsed = value.trim() ? (JSON.parse(value) as Record<string, string>) : {};
      setForm(prev => ({ ...prev, working_hours: parsed }));
    } catch {
      // не парсим при ошибке, просто держим текст в textarea через placeholder
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Магазины</h1>
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
          <div className="p-4 text-sm text-red-600">Не удалось загрузить магазины.</div>
        ) : stores.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Магазины ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Название</th>
                  <th className="px-3 py-2 text-left">Город</th>
                  <th className="px-3 py-2 text-left">Адрес</th>
                  <th className="px-3 py-2 text-left">Телефон</th>
                  <th className="px-3 py-2 text-left">Email</th>
                  <th className="px-3 py-2 text-left">Активен</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {stores.map(store => {
                  const createdAt = new Date(store.created_at);
                  return (
                    <tr
                      key={store.id}
                      className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                    >
                      <td className="px-3 py-2 text-sm text-zinc-900">{store.name}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{store.city}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{store.address}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{store.phone || '—'}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{store.email || '—'}</td>
                      <td className="px-3 py-2 text-xs">
                        {store.is_active ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Активен
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Выключен
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="mr-2 text-[var(--color-brand)] hover:underline"
                          onClick={() => handleEdit(store)}
                        >
                          Редактировать
                        </button>
                        <button
                          type="button"
                          className="text-red-600 hover:underline"
                          onClick={() => {
                            if (
                              window.confirm(
                                'Удалить этот магазин? Убедитесь, что он не используется в активных заказах.'
                              )
                            ) {
                              deleteMutation.mutate(store.id);
                            }
                          }}
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

      <Card className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-zinc-900">
          {editingId ? 'Редактирование магазина' : 'Новый магазин'}
        </h2>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Название</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
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
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Город</label>
              <input
                type="text"
                value={form.city}
                onChange={e => setForm({ ...form, city: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Адрес</label>
              <input
                type="text"
                value={form.address}
                onChange={e => setForm({ ...form, address: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Телефон</label>
              <input
                type="text"
                value={form.phone ?? ''}
                onChange={e => setForm({ ...form, phone: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Email</label>
              <input
                type="email"
                value={form.email ?? ''}
                onChange={e => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Широта</label>
              <input
                type="text"
                value={form.latitude ?? ''}
                onChange={e => setForm({ ...form, latitude: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Долгота</label>
              <input
                type="text"
                value={form.longitude ?? ''}
                onChange={e => setForm({ ...form, longitude: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Часы работы (JSON)</label>
            <textarea
              defaultValue={
                form.working_hours && Object.keys(form.working_hours).length > 0
                  ? JSON.stringify(form.working_hours, null, 2)
                  : ''
              }
              onBlur={e => handleWorkingHoursChange(e.target.value)}
              className="min-h-[80px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-xs font-mono"
              placeholder='например: {"monday": "9:00-21:00", "tuesday": "9:00-21:00"}'
            />
          </div>
          {editingId ? (
            <div className="space-y-2 rounded-lg border border-dashed border-zinc-200 p-3">
              <label className="block text-xs font-medium text-zinc-500">Фото магазина</label>
              <input
                type="file"
                accept="image/*"
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (file) uploadImageMutation.mutate(file);
                  e.target.value = '';
                }}
                className="block w-full text-xs text-zinc-500"
              />
              {storeImages.length > 0 ? (
                <ul className="flex flex-wrap gap-3">
                  {storeImages.map(img => {
                    const src = img.image_url ? getMediaUrl(img.image_url) : null;
                    return (
                      <li
                        key={img.id}
                        className="relative h-20 w-28 overflow-hidden rounded-lg border border-zinc-200"
                      >
                        {src ? (
                          <Image
                            src={src}
                            alt={img.alt_text ?? ''}
                            fill
                            className="object-cover"
                            sizes="112px"
                            unoptimized={src.startsWith('http')}
                          />
                        ) : null}
                        <button
                          type="button"
                          className="absolute right-1 top-1 rounded bg-white/90 px-1 text-xs text-red-600"
                          onClick={() => {
                            if (window.confirm('Удалить фото?')) {
                              deleteImageMutation.mutate(img.id);
                            }
                          }}
                        >
                          ×
                        </button>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="text-xs text-zinc-400">Нет загруженных фото.</p>
              )}
            </div>
          ) : null}

          <div className="flex items-center justify-between">
            <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
              <input
                type="checkbox"
                checked={form.is_active ?? false}
                onChange={e => setForm({ ...form, is_active: e.target.checked })}
              />
              Магазин активен
            </label>
            <div className="flex gap-2">
              {editingId && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setEditingId(null);
                    setForm({
                      name: '',
                      slug: '',
                      address: '',
                      city: '',
                      phone: '',
                      email: '',
                      latitude: '',
                      longitude: '',
                      working_hours: {},
                      is_active: true,
                    });
                  }}
                >
                  Отмена
                </Button>
              )}
              <Button
                type="submit"
                size="sm"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {editingId ? 'Сохранить' : 'Создать магазин'}
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
}
