'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import type { AdminProductPayload } from '@/lib/api/services/adminProducts.service';
import {
  createAdminProduct,
  uploadProductImage,
} from '@/lib/api/services/adminProducts.service';
import { getAdminCategories, type AdminCategory } from '@/lib/api/services/adminCatalog.service';
import { slugifyProductTitle } from '@/lib/slugify';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading, Spinner } from '@/components/ui/Loading';

const emptyForm: AdminProductPayload = {
  title: '',
  slug: '',
  category: '',
  price: '',
  old_price: '',
  sku: '',
  brand: '',
  description: '',
  short_description: '',
  is_active: true,
  is_featured: false,
};

export default function AdminProductCreatePage() {
  const router = useRouter();
  const [form, setForm] = useState<AdminProductPayload>(emptyForm);
  const [slugTouched, setSlugTouched] = useState(false);
  const [pendingImages, setPendingImages] = useState<File[]>([]);

  const {
    data: categories = [],
    isLoading: categoriesLoading,
    isError: categoriesError,
  } = useQuery({
    queryKey: ['admin', 'categories'],
    queryFn: getAdminCategories,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: AdminProductPayload) => {
      const body: AdminProductPayload = { ...payload };
      if (!body.slug?.trim()) {
        delete body.slug;
      }
      const product = await createAdminProduct(body);
      for (let i = 0; i < pendingImages.length; i++) {
        await uploadProductImage(product.id, pendingImages[i]!, {
          is_main: i === 0,
          sort_order: i,
        });
      }
      return product;
    },
    onSuccess: product => {
      router.replace(`/admin/products/${product.id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.category || !form.price) {
      return;
    }
    createMutation.mutate({
      ...form,
      price: form.price || '0',
      old_price: form.old_price || null,
      sku: form.sku || null,
      brand: form.brand || null,
      short_description: form.short_description || '',
      description: form.description || '',
    });
  };

  const handleChange = <K extends keyof AdminProductPayload>(
    field: K,
    value: AdminProductPayload[K]
  ) => {
    setForm(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const slugPreview = form.slug?.trim() || slugifyProductTitle(form.title);

  const isSubmitting = createMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Новый товар</h1>
      </div>

      <Card className="p-4">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Название *</label>
              <input
                type="text"
                value={form.title}
                onChange={e => {
                  const title = e.target.value;
                  handleChange('title', title);
                  if (!slugTouched) {
                    handleChange('slug', slugifyProductTitle(title));
                  }
                }}
                onBlur={() => {
                  if (!slugTouched && form.title.trim()) {
                    handleChange('slug', slugifyProductTitle(form.title));
                  }
                }}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">
                Slug <span className="font-normal text-zinc-400">(необязательно)</span>
              </label>
              <input
                type="text"
                value={form.slug ?? ''}
                onChange={e => {
                  setSlugTouched(true);
                  handleChange('slug', e.target.value);
                }}
                placeholder={slugPreview}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
              <p className="text-xs text-zinc-400">Будет: {slugPreview}</p>
            </div>
          </div>

          <div className="space-y-2 rounded-lg border border-dashed border-zinc-200 p-3">
            <label className="block text-xs font-medium text-zinc-500">Фото товара</label>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={e => {
                const files = e.target.files ? Array.from(e.target.files) : [];
                if (files.length) setPendingImages(prev => [...prev, ...files]);
                e.target.value = '';
              }}
              className="block w-full text-xs text-zinc-500"
            />
            {pendingImages.length > 0 && (
              <ul className="flex flex-wrap gap-2">
                {pendingImages.map((f, i) => (
                  <li
                    key={`${f.name}-${i}`}
                    className="flex items-center gap-2 rounded-lg bg-zinc-50 px-2 py-1 text-xs text-zinc-600"
                  >
                    {f.name}
                    <button
                      type="button"
                      className="text-red-600 hover:underline"
                      onClick={() =>
                        setPendingImages(prev => prev.filter((_, idx) => idx !== i))
                      }
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-zinc-400">
              Загрузятся после создания товара (можно добавить ещё на странице редактирования).
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Категория *</label>
              {categoriesLoading ? (
                <div className="flex h-9 items-center text-xs text-zinc-500">
                  Загрузка категорий...
                </div>
              ) : categoriesError ? (
                <div className="text-xs text-red-600">Не удалось загрузить категории.</div>
              ) : (
                <select
                  value={form.category}
                  onChange={e => handleChange('category', e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
                  required
                >
                  <option value="">Выберите категорию</option>
                  {categories.map((cat: AdminCategory) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.title}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Артикул (SKU)</label>
              <input
                type="text"
                value={form.sku ?? ''}
                onChange={e => handleChange('sku', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Бренд</label>
              <input
                type="text"
                value={form.brand ?? ''}
                onChange={e => handleChange('brand', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Цена *</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.price}
                onChange={e => handleChange('price', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Старая цена</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.old_price ?? ''}
                onChange={e => handleChange('old_price', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>

            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_active ?? false}
                  onChange={e => handleChange('is_active', e.target.checked)}
                />
                Активен
              </label>
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_featured ?? false}
                  onChange={e => handleChange('is_featured', e.target.checked)}
                />
                Рекомендованный
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Краткое описание</label>
            <textarea
              value={form.short_description ?? ''}
              onChange={e => handleChange('short_description', e.target.value)}
              className="min-h-[60px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Полное описание</label>
            <textarea
              value={form.description ?? ''}
              onChange={e => handleChange('description', e.target.value)}
              className="min-h-[120px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>

          <div className="mt-4 flex items-center justify-between">
            {isSubmitting && (
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <Spinner size="sm" />
                <span>Сохранение...</span>
              </div>
            )}
            <div className="ml-auto flex gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => router.back()}>
                Отмена
              </Button>
              <Button type="submit" size="sm" disabled={isSubmitting}>
                Создать товар
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  );
}
