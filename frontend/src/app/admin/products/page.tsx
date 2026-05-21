'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Download, Plus, RefreshCw, Sparkles } from 'lucide-react';
import Link from 'next/link';
import {
  getAdminProducts,
  type AdminProductListItem,
  type AdminProductListParams,
  bulkSetActive,
  bulkUpdatePrices,
  exportProductsCsv,
} from '@/lib/api/services/adminProducts.service';
import { getAdminCategories, type AdminCategory } from '@/lib/api/services/adminCatalog.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

export default function AdminProductsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [brand, setBrand] = useState('');
  const [isActive, setIsActive] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [priceMode, setPriceMode] = useState<'percent' | 'absolute'>('percent');
  const [priceDirection, setPriceDirection] = useState<'increase' | 'decrease'>('increase');
  const [priceField, setPriceField] = useState<'price' | 'old_price'>('price');
  const [priceValue, setPriceValue] = useState<string>('0');

  const params: AdminProductListParams = {
    page,
    search: search || undefined,
    category: category || undefined,
    brand: brand || undefined,
    is_active: isActive || undefined,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'products', params],
    queryFn: () => getAdminProducts(params),
  });

  const {
    data: categories = [],
    isLoading: categoriesLoading,
    isError: categoriesError,
  } = useQuery({
    queryKey: ['admin', 'categories'],
    queryFn: getAdminCategories,
  });

  const bulkSetActiveMutation = useMutation({
    mutationFn: bulkSetActive,
    onSuccess: () => {
      void refetch();
      setSelected(new Set());
    },
  });

  const bulkUpdatePricesMutation = useMutation({
    mutationFn: bulkUpdatePrices,
    onSuccess: () => {
      void refetch();
      setIsPriceModalOpen(false);
      setPriceValue('0');
    },
  });

  const handleExport = async () => {
    try {
      const blob = await exportProductsCsv(params);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'products.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // можно добавить toast при наличии общей системы уведомлений
    }
  };

  const products: AdminProductListItem[] = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = products.length > 0 ? products.length : 20;
  const totalPages = pageSize > 0 ? Math.ceil(total / pageSize) : 1;

  const selectedCount = selected.size;

  const toggleSelectAllOnPage = () => {
    if (products.length === 0) return;
    const allIds = products.map(p => p.id);
    const allSelected = allIds.every(id => selected.has(id));
    if (allSelected) {
      const next = new Set(selected);
      allIds.forEach(id => next.delete(id));
      setSelected(next);
    } else {
      const next = new Set(selected);
      allIds.forEach(id => next.add(id));
      setSelected(next);
    }
  };

  const toggleSelectOne = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelected(next);
  };

  const handleBulkSetActive = (value: boolean) => {
    if (selected.size === 0) return;
    bulkSetActiveMutation.mutate({
      product_ids: Array.from(selected),
      is_active: value,
    });
  };

  const handleBulkUpdatePrices = () => {
    if (selected.size === 0) return;
    const numericValue = Number(priceValue.replace(',', '.'));
    if (!Number.isFinite(numericValue) || numericValue < 0) {
      return;
    }
    bulkUpdatePricesMutation.mutate({
      product_ids: Array.from(selected),
      mode: priceMode,
      value: numericValue,
      direction: priceDirection,
      field: priceField,
    });
  };

  const categoriesMap = useMemo(() => {
    const map: Record<string, AdminCategory> = {};
    for (const c of categories) {
      map[c.id] = c;
    }
    return map;
  }, [categories]);

  const isAllPageSelected =
    products.length > 0 && products.every(product => selected.has(product.id));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Товары</h1>
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={products.length === 0}
          >
            <Download className="mr-2 h-4 w-4" />
            Экспорт CSV
          </Button>
          <Link href="/admin/products/new">
            <Button type="button" size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Новый товар
            </Button>
          </Link>
        </div>
      </div>

      {/* Фильтры */}
      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-4">
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Категория</label>
            <select
              value={category}
              onChange={e => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
              disabled={categoriesLoading || categoriesError}
            >
              <option value="">Все</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.title}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Бренд</label>
            <input
              type="text"
              value={brand}
              onChange={e => {
                setBrand(e.target.value);
                setPage(1);
              }}
              placeholder="Например, Apple"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Статус</label>
            <select
              value={isActive}
              onChange={e => {
                setIsActive(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Все</option>
              <option value="true">Активные</option>
              <option value="false">Отключенные</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Поиск</label>
            <input
              type="text"
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Название или артикул"
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="text-xs text-zinc-500">
            Показано {products.length} из {total} товаров.
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setCategory('');
              setBrand('');
              setIsActive('');
              setSearch('');
              setPage(1);
            }}
          >
            Сбросить фильтры
          </Button>
        </div>
      </Card>

      {/* Массовые операции */}
      {selectedCount > 0 && (
        <Card className="flex flex-col gap-3 border-dashed border-zinc-300 bg-zinc-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-zinc-700">
            <Sparkles className="h-4 w-4 text-[var(--color-brand)]" />
            <span>
              Выбрано товаров: <span className="font-semibold">{selectedCount}</span>
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handleBulkSetActive(true)}
              disabled={bulkSetActiveMutation.isPending}
            >
              Активировать
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => handleBulkSetActive(false)}
              disabled={bulkSetActiveMutation.isPending}
            >
              Деактивировать
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setIsPriceModalOpen(true)}
              disabled={bulkUpdatePricesMutation.isPending}
            >
              Изменить цены
            </Button>
          </div>
        </Card>
      )}

      {/* Таблица товаров */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="flex min-h-[260px] items-center justify-center">
            <Loading />
          </div>
        ) : isError ? (
          <div className="p-4 text-sm text-red-600">Не удалось загрузить товары.</div>
        ) : products.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Товары ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[900px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">
                    <input
                      type="checkbox"
                      checked={isAllPageSelected}
                      onChange={toggleSelectAllOnPage}
                    />
                  </th>
                  <th className="px-3 py-2 text-left">Название</th>
                  <th className="px-3 py-2 text-left">Артикул</th>
                  <th className="px-3 py-2 text-left">Категория</th>
                  <th className="px-3 py-2 text-right">Цена</th>
                  <th className="px-3 py-2 text-right">Старая цена</th>
                  <th className="px-3 py-2 text-center">Статус</th>
                  <th className="px-3 py-2 text-center">В наличии</th>
                  <th className="px-3 py-2 text-right">Создан</th>
                </tr>
              </thead>
              <tbody>
                {products.map(product => {
                  const categoryTitle =
                    product.category?.title ??
                    (product.category?.id ? categoriesMap[product.category.id]?.title : '') ??
                    '';
                  const inStock = (product.available_quantity_total ?? 0) > 0;
                  const createdAt = new Date(product.created_at);
                  const created =
                    Number.isNaN(createdAt.getTime()) === false
                      ? createdAt.toLocaleDateString()
                      : '';
                  const isSelected = selected.has(product.id);
                  return (
                    <tr
                      key={product.id}
                      className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50"
                    >
                      <td className="px-3 py-2 align-middle">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelectOne(product.id)}
                        />
                      </td>
                      <td className="px-3 py-2 align-middle text-sm text-zinc-900">
                        <Link
                          href={`/admin/products/${product.id}`}
                          className="text-[var(--color-brand)] hover:underline"
                        >
                          {product.title}
                        </Link>
                      </td>
                      <td className="px-3 py-2 align-middle text-xs text-zinc-500">
                        {product.sku || '—'}
                      </td>
                      <td className="px-3 py-2 align-middle text-xs text-zinc-500">
                        {categoryTitle || '—'}
                      </td>
                      <td className="px-3 py-2 align-middle text-right text-sm text-zinc-900">
                        {product.price}
                      </td>
                      <td className="px-3 py-2 align-middle text-right text-xs text-zinc-500">
                        {product.old_price || '—'}
                      </td>
                      <td className="px-3 py-2 align-middle text-center text-xs">
                        {product.is_active ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Активен
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Выключен
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 align-middle text-center text-xs">
                        {inStock ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" />
                            {product.available_quantity_total}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            <span className="h-2 w-2 rounded-full bg-zinc-400" />0
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 align-middle text-right text-xs text-zinc-500">
                        {created}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Пагинация */}
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

      {/* Модалка изменения цен */}
      {isPriceModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
            <h2 className="mb-3 text-base font-semibold text-zinc-900">Массовое изменение цен</h2>
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">Поле</label>
                <select
                  value={priceField}
                  onChange={e => setPriceField(e.target.value as 'price' | 'old_price')}
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                >
                  <option value="price">Текущая цена</option>
                  <option value="old_price">Старая цена</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">Режим</label>
                <select
                  value={priceMode}
                  onChange={e => setPriceMode(e.target.value as 'percent' | 'absolute')}
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                >
                  <option value="percent">Процент</option>
                  <option value="absolute">Фиксированная сумма</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">Направление</label>
                <select
                  value={priceDirection}
                  onChange={e => setPriceDirection(e.target.value as 'increase' | 'decrease')}
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                >
                  <option value="increase">Увеличить</option>
                  <option value="decrease">Уменьшить</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-zinc-500">Значение</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={priceValue}
                  onChange={e => setPriceValue(e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                />
                <p className="text-xs text-zinc-500">
                  При режиме «Процент» укажите, например, 10 для изменения на 10%.
                </p>
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsPriceModalOpen(false)}
              >
                Отмена
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleBulkUpdatePrices}
                disabled={bulkUpdatePricesMutation.isPending}
              >
                Применить
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
