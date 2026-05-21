'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import {
  getStockByStoreCategories,
  getStockByStoreProducts,
  getStockStoresSummary,
  type StockCategoryRow,
  type StockStoreSummary,
} from '@/lib/api/services/adminStock.service';
import {
  updateAdminStock,
  type AdminStockItem,
} from '@/lib/api/services/adminProducts.service';

type Step = 'stores' | 'categories' | 'products';

export default function AdminStockPage() {
  const [step, setStep] = useState<Step>('stores');
  const [store, setStore] = useState<StockStoreSummary | null>(null);
  const [category, setCategory] = useState<StockCategoryRow | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  const { data: stores = [], isLoading: storesLoading, refetch: refetchStores } = useQuery({
    queryKey: ['admin', 'stock', 'stores-summary'],
    queryFn: getStockStoresSummary,
  });

  const { data: categories = [], isLoading: categoriesLoading } = useQuery({
    queryKey: ['admin', 'stock', 'categories', store?.id],
    queryFn: () => getStockByStoreCategories(store!.id),
    enabled: step !== 'stores' && !!store?.id,
  });

  const productsParams = {
    page,
    category: category?.category_id || undefined,
    search: search.trim() || undefined,
  };

  const {
    data: productsData,
    isLoading: productsLoading,
    refetch: refetchProducts,
  } = useQuery({
    queryKey: ['admin', 'stock', 'products', store?.id, productsParams],
    queryFn: () => getStockByStoreProducts(store!.id, productsParams),
    enabled: step === 'products' && !!store?.id,
  });

  const updateStockMutation = useMutation({
    mutationFn: (variables: {
      id: string;
      payload: Partial<Pick<AdminStockItem, 'quantity' | 'reserved_quantity'>>;
    }) => updateAdminStock(variables.id, variables.payload),
    onSuccess: () => {
      void refetchProducts();
      void refetchStores();
    },
  });

  const handleStockNumberChange = (id: string, value: string) => {
    const num = Number(value);
    if (!Number.isFinite(num) || num < 0) return;
    updateStockMutation.mutate({ id, payload: { quantity: num } });
  };

  const items: AdminStockItem[] = productsData?.results ?? [];
  const total = productsData?.count ?? 0;
  const pageSize = items.length > 0 ? items.length : 50;
  const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1;

  const goStores = () => {
    setStep('stores');
    setStore(null);
    setCategory(null);
    setPage(1);
    setSearch('');
  };

  const goCategories = (s: StockStoreSummary) => {
    setStore(s);
    setCategory(null);
    setStep('categories');
    setPage(1);
    setSearch('');
  };

  const goProducts = (c: StockCategoryRow) => {
    setCategory(c);
    setStep('products');
    setPage(1);
    setSearch('');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Остатки</h1>
          <nav className="mt-2 flex flex-wrap items-center gap-1 text-sm text-zinc-500">
            <button type="button" className="hover:text-zinc-900" onClick={goStores}>
              Магазины
            </button>
            {store ? (
              <>
                <span aria-hidden>/</span>
                <button
                  type="button"
                  className="hover:text-zinc-900"
                  onClick={() => {
                    setStep('categories');
                    setCategory(null);
                    setPage(1);
                  }}
                >
                  {store.name}
                </button>
              </>
            ) : null}
            {category && step === 'products' ? (
              <>
                <span aria-hidden>/</span>
                <span className="text-zinc-900">{category.title}</span>
              </>
            ) : null}
          </nav>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => refetchStores()}>
          Обновить
        </Button>
      </div>

      {step === 'stores' && (
        <Card className="p-4">
          {storesLoading ? (
            <div className="flex min-h-[200px] items-center justify-center">
              <Loading />
            </div>
          ) : stores.length === 0 ? (
            <p className="text-sm text-zinc-500">Нет магазинов.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {stores.map(s => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => goCategories(s)}
                  className="rounded-xl border border-zinc-200 bg-white p-4 text-left transition-colors hover:border-[var(--color-brand)] hover:shadow-sm"
                >
                  <p className="font-medium text-zinc-900">{s.name}</p>
                  <p className="text-xs text-zinc-500">{s.city}</p>
                  <p className="mt-2 text-xs text-zinc-600">
                    SKU: {s.total_skus}
                    {s.low_stock_count > 0 ? (
                      <span className="ml-2 text-amber-700">мало: {s.low_stock_count}</span>
                    ) : null}
                  </p>
                </button>
              ))}
            </div>
          )}
        </Card>
      )}

      {step === 'categories' && store && (
        <Card className="p-4">
          {categoriesLoading ? (
            <div className="flex min-h-[200px] items-center justify-center">
              <Loading />
            </div>
          ) : categories.length === 0 ? (
            <p className="text-sm text-zinc-500">Нет остатков в этом магазине.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {categories.map(c => (
                <button
                  key={c.category_id || '__none__'}
                  type="button"
                  onClick={() => goProducts(c)}
                  className="flex items-center justify-between rounded-lg border border-zinc-200 px-4 py-3 text-left hover:bg-zinc-50"
                >
                  <span className="font-medium text-zinc-900">{c.title}</span>
                  <span className="text-sm text-zinc-500">{c.stock_count} поз.</span>
                </button>
              ))}
            </div>
          )}
          <div className="mt-4">
            <Button type="button" variant="ghost" size="sm" onClick={goStores}>
              ← К магазинам
            </Button>
          </div>
        </Card>
      )}

      {step === 'products' && store && category && (
        <Card className="overflow-hidden">
          <div className="border-b border-zinc-200 p-4">
            <input
              type="search"
              placeholder="Поиск по названию или SKU"
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full max-w-md rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>
          {productsLoading ? (
            <div className="flex min-h-[200px] items-center justify-center">
              <Loading />
            </div>
          ) : items.length === 0 ? (
            <div className="p-4 text-sm text-zinc-500">Товары не найдены.</div>
          ) : (
            <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                    <th className="px-3 py-2 text-left">Товар</th>
                    <th className="px-3 py-2 text-left">Доступно</th>
                    <th className="px-3 py-2 text-left">Количество</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(row => (
                    <tr key={row.id} className="border-b border-zinc-100">
                      <td className="px-3 py-2">
                        <Link
                          href={`/admin/products/${row.product}`}
                          className="text-[var(--color-brand)] hover:underline"
                        >
                          {row.product_title}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">{row.available_quantity}</td>
                      <td className="px-3 py-2">
                        <input
                          type="number"
                          min={0}
                          defaultValue={row.quantity}
                          onBlur={e => handleStockNumberChange(row.id, e.target.value)}
                          className="w-24 rounded-lg border border-zinc-200 px-2 py-1 text-sm"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-zinc-200 px-4 py-3 text-xs text-zinc-500">
              <span>
                Стр. {page} из {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                >
                  Назад
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Вперёд
                </Button>
              </div>
            </div>
          )}
          <div className="border-t border-zinc-200 p-4">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setStep('categories');
                setCategory(null);
                setPage(1);
              }}
            >
              ← К категориям
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
