'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useParams } from 'next/navigation';
import {
  getAdminProduct,
  updateAdminProduct,
  deleteAdminProduct,
  type AdminProductPayload,
  uploadProductImage,
  updateProductImage,
  deleteProductImage,
  createProductSpec,
  updateProductSpec,
  deleteProductSpec,
  getAdminStockByProduct,
  updateAdminStock,
  type AdminStockItem,
} from '@/lib/api/services/adminProducts.service';
import { getAdminCategories, type AdminCategory } from '@/lib/api/services/adminCatalog.service';
import { slugifyProductTitle } from '@/lib/slugify';
import type { ProductDetail, ProductSpec } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading, Spinner } from '@/components/ui/Loading';

interface RouteParams {
  id: string;
}

export default function AdminProductEditPage() {
  const params = useParams() as unknown as RouteParams;
  const productId = params.id;

  const [form, setForm] = useState<AdminProductPayload | null>(null);
  const [formSyncKey, setFormSyncKey] = useState<string | null>(null);
  const [newSpec, setNewSpec] = useState<{ name: string; value: string }>({
    name: '',
    value: '',
  });

  const {
    data: product,
    isLoading: productLoading,
    isError: productError,
    refetch: refetchProduct,
  } = useQuery({
    queryKey: ['admin', 'product', productId],
    queryFn: () => getAdminProduct(productId),
  });

  const {
    data: categories = [],
    isLoading: categoriesLoading,
    isError: categoriesError,
  } = useQuery({
    queryKey: ['admin', 'categories'],
    queryFn: getAdminCategories,
  });

  const {
    data: stockData,
    isLoading: stockLoading,
    isError: stockError,
    refetch: refetchStock,
  } = useQuery({
    queryKey: ['admin', 'product-stock', productId],
    queryFn: () => getAdminStockByProduct(productId),
  });

  const updateProductMutation = useMutation({
    mutationFn: (payload: AdminProductPayload) => updateAdminProduct(productId, payload),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const deleteProductMutation = useMutation({
    mutationFn: () => deleteAdminProduct(productId),
    onSuccess: () => {
      window.location.href = '/admin/products';
    },
  });

  const uploadImageMutation = useMutation({
    mutationFn: (file: File) => uploadProductImage(productId, file),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const updateImageMutation = useMutation({
    mutationFn: (variables: {
      id: string;
      payload: { alt_text?: string | null; is_main?: boolean };
    }) => updateProductImage(variables.id, variables.payload),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: (id: string) => deleteProductImage(id),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const createSpecMutation = useMutation({
    mutationFn: (variables: { name: string; value: string }) =>
      createProductSpec(productId, { name: variables.name, value: variables.value }),
    onSuccess: () => {
      setNewSpec({ name: '', value: '' });
      void refetchProduct();
    },
  });

  const updateSpecMutation = useMutation({
    mutationFn: (variables: { id: string; payload: { name: string; value: string } }) =>
      updateProductSpec(variables.id, variables.payload),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const deleteSpecMutation = useMutation({
    mutationFn: (id: string) => deleteProductSpec(id),
    onSuccess: () => {
      void refetchProduct();
    },
  });

  const updateStockMutation = useMutation({
    mutationFn: (variables: {
      id: string;
      payload: Partial<Pick<AdminStockItem, 'quantity' | 'reserved_quantity'>>;
    }) => updateAdminStock(variables.id, variables.payload),
    onSuccess: () => {
      void refetchStock();
      void refetchProduct();
    },
  });

  const desiredFormKey = product ? `${product.id}:${product.updated_at}` : null;
  if (product && desiredFormKey !== null && desiredFormKey !== formSyncKey) {
    setFormSyncKey(desiredFormKey);
    setForm({
      title: product.title,
      slug: product.slug,
      sku: product.sku,
      category: product.category?.id ?? '',
      brand: product.brand ?? '',
      price: product.price,
      old_price: product.old_price ?? '',
      description: product.description,
      short_description: product.short_description ?? '',
      is_active: product.is_active,
      is_featured: product.is_featured ?? false,
    });
  }

  const handleFormChange = <K extends keyof AdminProductPayload>(
    field: K,
    value: AdminProductPayload[K]
  ) => {
    setForm(prev =>
      prev
        ? {
            ...prev,
            [field]: value,
          }
        : prev
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    if (!form.title.trim() || !form.category || !form.price) {
      return;
    }
    updateProductMutation.mutate({
      ...form,
      price: form.price || '0',
      old_price: form.old_price || null,
      sku: form.sku || null,
      brand: form.brand || null,
      short_description: form.short_description || '',
      description: form.description || '',
    });
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    uploadImageMutation.mutate(file);
    e.target.value = '';
  };

  const handleStockNumberChange = (
    id: string,
    field: 'quantity' | 'reserved_quantity',
    value: string
  ) => {
    const num = Number(value);
    if (!Number.isFinite(num) || num < 0) return;
    updateStockMutation.mutate({ id, payload: { [field]: num } });
  };

  if (productLoading || !product || !form) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (productError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Не удалось загрузить товар.
      </div>
    );
  }

  const specs: ProductSpec[] = product.specs ?? [];
  const stockItems: AdminStockItem[] = stockData?.results ?? [];
  const productImages = product.images ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Редактирование товара</h1>
          <div className="mt-1 text-sm text-zinc-500">
            ID: <span className="font-mono">{product.id}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              if (window.confirm('Удалить этот товар без возможности восстановления?')) {
                deleteProductMutation.mutate();
              }
            }}
            disabled={deleteProductMutation.isPending}
          >
            Удалить товар
          </Button>
        </div>
      </div>

      {/* Основная форма */}
      <Card className="p-4">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Название *</label>
              <input
                type="text"
                value={form.title}
                onChange={e => handleFormChange('title', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Slug</label>
              <input
                type="text"
                value={form.slug ?? ''}
                onChange={e => handleFormChange('slug', e.target.value)}
                placeholder={slugifyProductTitle(form.title)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
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
                  onChange={e => handleFormChange('category', e.target.value)}
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
                onChange={e => handleFormChange('sku', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Бренд</label>
              <input
                type="text"
                value={form.brand ?? ''}
                onChange={e => handleFormChange('brand', e.target.value)}
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
                onChange={e => handleFormChange('price', e.target.value)}
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
                onChange={e => handleFormChange('old_price', e.target.value)}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>

            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_active ?? false}
                  onChange={e => handleFormChange('is_active', e.target.checked)}
                />
                Активен
              </label>
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_featured ?? false}
                  onChange={e => handleFormChange('is_featured', e.target.checked)}
                />
                Рекомендованный
              </label>
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Краткое описание</label>
            <textarea
              value={form.short_description ?? ''}
              onChange={e => handleFormChange('short_description', e.target.value)}
              className="min-h-[60px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Полное описание</label>
            <textarea
              value={form.description ?? ''}
              onChange={e => handleFormChange('description', e.target.value)}
              className="min-h-[120px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>

          <div className="mt-4 flex items-center justify-between">
            {updateProductMutation.isPending && (
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <Spinner size="sm" />
                <span>Сохранение...</span>
              </div>
            )}
            <Button
              type="submit"
              size="sm"
              className="ml-auto"
              disabled={updateProductMutation.isPending}
            >
              Сохранить изменения
            </Button>
          </div>
        </form>
      </Card>

      {/* Изображения */}
      <Card className="space-y-4 p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-zinc-900">Изображения</h2>
          <label className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-[var(--color-brand)]">
            <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
            Добавить изображение
          </label>
        </div>

        {uploadImageMutation.isPending && (
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <Spinner size="sm" />
            <span>Загрузка изображения...</span>
          </div>
        )}

        {productImages.length === 0 ? (
          <div className="text-sm text-zinc-500">Изображения ещё не загружены.</div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-3 md:grid-cols-4">
            {productImages.map(img => (
              <div
                key={img.id}
                className="flex flex-col gap-2 rounded-lg border border-zinc-200 p-2"
              >
                <div className="aspect-square overflow-hidden rounded-md bg-zinc-100">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.image}
                    alt={img.alt_text ?? ''}
                    className="h-full w-full object-cover"
                  />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs text-zinc-500">
                    {img.is_main ? 'Главное' : 'Дополнительное'}
                  </span>
                  <div className="flex gap-1">
                    {!img.is_main && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          updateImageMutation.mutate({
                            id: img.id,
                            payload: { is_main: true },
                          })
                        }
                      >
                        Сделать главным
                      </Button>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => deleteImageMutation.mutate(img.id)}
                    >
                      Удалить
                    </Button>
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-zinc-500">Alt-текст</label>
                  <input
                    type="text"
                    defaultValue={img.alt_text ?? ''}
                    onBlur={e =>
                      updateImageMutation.mutate({
                        id: img.id,
                        payload: { alt_text: e.target.value },
                      })
                    }
                    className="w-full rounded-lg border border-zinc-200 px-2 py-1 text-xs"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Характеристики */}
      <Card className="space-y-4 p-4">
        <h2 className="text-sm font-semibold text-zinc-900">Характеристики</h2>
        {specs.length === 0 ? (
          <div className="text-sm text-zinc-500">Характеристики ещё не добавлены.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[500px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Название</th>
                  <th className="px-3 py-2 text-left">Значение</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {specs.map(spec => (
                  <tr key={spec.name + spec.value} className="border-b border-zinc-100">
                    <td className="px-3 py-2 align-middle">
                      <input
                        type="text"
                        defaultValue={spec.name}
                        className="w-full rounded-lg border border-zinc-200 px-2 py-1 text-xs"
                        onBlur={e =>
                          updateSpecMutation.mutate({
                            id: (spec as unknown as { id: string }).id,
                            payload: { name: e.target.value, value: spec.value },
                          })
                        }
                      />
                    </td>
                    <td className="px-3 py-2 align-middle">
                      <input
                        type="text"
                        defaultValue={spec.value}
                        className="w-full rounded-lg border border-zinc-200 px-2 py-1 text-xs"
                        onBlur={e =>
                          updateSpecMutation.mutate({
                            id: (spec as unknown as { id: string }).id,
                            payload: { name: spec.name, value: e.target.value },
                          })
                        }
                      />
                    </td>
                    <td className="px-3 py-2 align-middle text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          deleteSpecMutation.mutate((spec as unknown as { id: string }).id)
                        }
                      >
                        Удалить
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-3 border-t border-dashed border-zinc-200 pt-3">
          <h3 className="mb-2 text-xs font-semibold text-zinc-700">Добавить характеристику</h3>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              placeholder="Название"
              value={newSpec.name}
              onChange={e => setNewSpec(prev => ({ ...prev, name: e.target.value }))}
              className="flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Значение"
              value={newSpec.value}
              onChange={e => setNewSpec(prev => ({ ...prev, value: e.target.value }))}
              className="flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
            <Button
              type="button"
              size="sm"
              onClick={() => {
                if (!newSpec.name.trim() || !newSpec.value.trim()) return;
                createSpecMutation.mutate({
                  name: newSpec.name.trim(),
                  value: newSpec.value.trim(),
                });
              }}
            >
              Добавить
            </Button>
          </div>
        </div>
      </Card>

      {/* Остатки по магазинам */}
      <Card className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-900">Остатки по магазинам</h2>
        </div>

        {stockLoading ? (
          <div className="flex min-h-[120px] items-center justify-center">
            <Loading />
          </div>
        ) : stockError ? (
          <div className="text-sm text-red-600">Не удалось загрузить остатки по магазинам.</div>
        ) : stockItems.length === 0 ? (
          <div className="text-sm text-zinc-500">
            Для этого товара пока нет остатков в магазинах.
          </div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[600px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Магазин</th>
                  <th className="px-3 py-2 text-right">Количество</th>
                  <th className="px-3 py-2 text-right">Зарезервировано</th>
                  <th className="px-3 py-2 text-right">Доступно</th>
                </tr>
              </thead>
              <tbody>
                {stockItems.map(item => (
                  <tr key={item.id} className="border-b border-zinc-100 last:border-0">
                    <td className="px-3 py-2 align-middle text-sm text-zinc-900">
                      {item.store_name}
                    </td>
                    <td className="px-3 py-2 align-middle text-right">
                      <input
                        type="number"
                        min={0}
                        defaultValue={item.quantity}
                        onBlur={e => handleStockNumberChange(item.id, 'quantity', e.target.value)}
                        className="w-24 rounded-lg border border-zinc-200 px-2 py-1 text-right text-xs"
                      />
                    </td>
                    <td className="px-3 py-2 align-middle text-right">
                      <input
                        type="number"
                        min={0}
                        defaultValue={item.reserved_quantity}
                        onBlur={e =>
                          handleStockNumberChange(item.id, 'reserved_quantity', e.target.value)
                        }
                        className="w-24 rounded-lg border border-zinc-200 px-2 py-1 text-right text-xs"
                      />
                    </td>
                    <td className="px-3 py-2 align-middle text-right text-xs text-zinc-700">
                      {item.available_quantity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
