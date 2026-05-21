'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import {
  getAdminPromotions,
  getAdminPromoCodes,
  createAdminPromotion,
  updateAdminPromotion,
  deleteAdminPromotion,
  createAdminPromoCode,
  updateAdminPromoCode,
  deleteAdminPromoCode,
  type AdminPromotionListItem,
  type AdminPromoCodeListItem,
  type AdminPromotionPayload,
  type AdminPromoCodePayload,
} from '@/lib/api/services/adminPromotions.service';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';

type TabKey = 'promotions' | 'promocodes';

export default function AdminPromotionsPage() {
  const [tab, setTab] = useState<TabKey>('promotions');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900">Акции и промокоды</h1>
      </div>

      <div className="flex gap-2 border-b border-zinc-200">
        <TabButton
          active={tab === 'promotions'}
          onClick={() => setTab('promotions')}
          label="Акции"
        />
        <TabButton
          active={tab === 'promocodes'}
          onClick={() => setTab('promocodes')}
          label="Промокоды"
        />
      </div>

      {tab === 'promotions' && <PromotionsTab />}
      {tab === 'promocodes' && <PromoCodesTab />}
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

function PromotionsTab() {
  const [form, setForm] = useState<AdminPromotionPayload>({
    title: '',
    description: '',
    discount_type: 'percent',
    discount_value: '',
    start_date: '',
    end_date: '',
    is_active: true,
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'promotions', 'list'],
    queryFn: () => getAdminPromotions(),
  });

  const promotions: AdminPromotionListItem[] = data?.results ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: AdminPromotionPayload) => createAdminPromotion(payload),
    onSuccess: () => {
      void refetch();
      setForm({
        title: '',
        description: '',
        discount_type: 'percent',
        discount_value: '',
        start_date: '',
        end_date: '',
        is_active: true,
      });
      setEditingId(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (variables: { id: string; payload: Partial<AdminPromotionPayload> }) =>
      updateAdminPromotion(variables.id, variables.payload),
    onSuccess: () => {
      void refetch();
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminPromotion(id),
    onSuccess: () => {
      void refetch();
      if (editingId === null) return;
      setEditingId(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    if (!form.discount_value) return;
    if (!form.start_date || !form.end_date) return;
    const payload: AdminPromotionPayload = {
      ...form,
      discount_value: form.discount_value,
      description: form.description || '',
      is_active: form.is_active ?? true,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (promo: AdminPromotionListItem) => {
    setEditingId(promo.id);
    setForm({
      title: promo.title,
      description: (promo as { description?: string | null }).description ?? '',
      discount_type: promo.discount_type,
      discount_value: promo.discount_value,
      start_date: promo.start_date ?? '',
      end_date: promo.end_date ?? '',
      is_active: promo.is_active,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-900">Акции</h2>
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
          <div className="p-4 text-sm text-red-600">Не удалось загрузить акции.</div>
        ) : promotions.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Акции ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Название</th>
                  <th className="px-3 py-2 text-left">Тип скидки</th>
                  <th className="px-3 py-2 text-right">Значение</th>
                  <th className="px-3 py-2 text-left">Период</th>
                  <th className="px-3 py-2 text-left">Активна</th>
                  <th className="px-3 py-2 text-left">Создана</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {promotions.map(promo => {
                  const start = promo.start_date ? new Date(promo.start_date) : null;
                  const end = promo.end_date ? new Date(promo.end_date) : null;
                  const created = promo.created_at ? new Date(promo.created_at) : null;
                  return (
                    <tr key={promo.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{promo.title}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {promo.discount_type === 'percent' ? 'Процент' : 'Фиксированная'}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-zinc-900">
                        {promo.discount_value}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {start && !Number.isNaN(start.getTime()) ? start.toLocaleDateString() : '—'}{' '}
                        — {end && !Number.isNaN(end.getTime()) ? end.toLocaleDateString() : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {promo.is_active ? (
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
                        {created && !Number.isNaN(created.getTime())
                          ? created.toLocaleString()
                          : '—'}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="mr-2 text-[var(--color-brand)] hover:underline"
                          onClick={() => handleEdit(promo)}
                        >
                          Редактировать
                        </button>
                        <button
                          type="button"
                          className="text-red-600 hover:underline"
                          onClick={() => deleteMutation.mutate(promo.id)}
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
        <h3 className="text-sm font-semibold text-zinc-900">
          {editingId ? 'Редактирование акции' : 'Новая акция'}
        </h3>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Название</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              required
            />
          </div>
          <div className="space-y-1">
            <label className="block text-xs font-medium text-zinc-500">Описание</label>
            <textarea
              value={form.description ?? ''}
              onChange={e => setForm({ ...form, description: e.target.value })}
              className="min-h-[80px] w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Тип скидки</label>
              <select
                value={form.discount_type}
                onChange={e =>
                  setForm({
                    ...form,
                    discount_type: e.target.value as 'percent' | 'fixed',
                  })
                }
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
              >
                <option value="percent">Процент</option>
                <option value="fixed">Фиксированная сумма</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Значение</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.discount_value}
                onChange={e => setForm({ ...form, discount_value: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_active ?? false}
                  onChange={e => setForm({ ...form, is_active: e.target.checked })}
                />
                Активна
              </label>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата начала</label>
              <input
                type="datetime-local"
                value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата окончания</label>
              <input
                type="datetime-local"
                value={form.end_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            {editingId && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEditingId(null);
                  setForm({
                    title: '',
                    description: '',
                    discount_type: 'percent',
                    discount_value: '',
                    start_date: '',
                    end_date: '',
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
              {editingId ? 'Сохранить' : 'Создать акцию'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function PromoCodesTab() {
  const [form, setForm] = useState<AdminPromoCodePayload>({
    code: '',
    discount_type: 'percent',
    discount_value: '',
    max_uses: null,
    min_order_amount: '',
    start_date: '',
    end_date: '',
    is_active: true,
  });
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'promotions', 'promocodes'],
    queryFn: () => getAdminPromoCodes(),
  });

  const items: AdminPromoCodeListItem[] = data?.results ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: AdminPromoCodePayload) => createAdminPromoCode(payload),
    onSuccess: () => {
      void refetch();
      setForm({
        code: '',
        discount_type: 'percent',
        discount_value: '',
        max_uses: null,
        min_order_amount: '',
        start_date: '',
        end_date: '',
        is_active: true,
      });
      setEditingId(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (variables: { id: string; payload: Partial<AdminPromoCodePayload> }) =>
      updateAdminPromoCode(variables.id, variables.payload),
    onSuccess: () => {
      void refetch();
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdminPromoCode(id),
    onSuccess: () => {
      void refetch();
      if (editingId === null) return;
      setEditingId(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.code.trim()) return;
    if (!form.discount_value) return;
    if (!form.start_date || !form.end_date) return;
    const payload: AdminPromoCodePayload = {
      ...form,
      discount_value: form.discount_value,
      min_order_amount: form.min_order_amount || null,
      is_active: form.is_active ?? true,
      max_uses: form.max_uses ?? null,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleEdit = (code: AdminPromoCodeListItem) => {
    setEditingId(code.id);
    setForm({
      code: code.code,
      discount_type: code.discount_type,
      discount_value: code.discount_value,
      max_uses: code.max_uses ?? null,
      min_order_amount: (code as { min_order_amount?: string | null }).min_order_amount ?? '',
      start_date: code.start_date ?? '',
      end_date: code.end_date ?? '',
      is_active: code.is_active,
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-900">Промокоды</h2>
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
          <div className="p-4 text-sm text-red-600">Не удалось загрузить промокоды.</div>
        ) : items.length === 0 ? (
          <div className="p-4 text-sm text-zinc-500">Промокоды ещё не созданы.</div>
        ) : (
          <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <table className="w-full min-w-[800px] text-sm">
              <thead>
                <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                  <th className="px-3 py-2 text-left">Код</th>
                  <th className="px-3 py-2 text-left">Тип скидки</th>
                  <th className="px-3 py-2 text-right">Значение</th>
                  <th className="px-3 py-2 text-right">Использований</th>
                  <th className="px-3 py-2 text-right">Лимит</th>
                  <th className="px-3 py-2 text-left">Период</th>
                  <th className="px-3 py-2 text-left">Активен</th>
                  <th className="px-3 py-2 text-right">Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.map(code => {
                  const start = code.start_date ? new Date(code.start_date) : null;
                  const end = code.end_date ? new Date(code.end_date) : null;
                  return (
                    <tr key={code.id} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 text-sm text-zinc-900">{code.code}</td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {code.discount_type === 'percent' ? 'Процент' : 'Фиксированная'}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-zinc-900">
                        {code.discount_value}
                      </td>
                      <td className="px-3 py-2 text-right text-xs text-zinc-600">
                        {code.used_count}
                      </td>
                      <td className="px-3 py-2 text-right text-xs text-zinc-600">
                        {code.max_uses ?? '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-zinc-600">
                        {start && !Number.isNaN(start.getTime()) ? start.toLocaleDateString() : '—'}{' '}
                        — {end && !Number.isNaN(end.getTime()) ? end.toLocaleDateString() : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {code.is_active ? (
                          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                            Да
                          </span>
                        ) : (
                          <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-zinc-500">
                            Нет
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-xs">
                        <button
                          type="button"
                          className="mr-2 text-[var(--color-brand)] hover:underline"
                          onClick={() => handleEdit(code)}
                        >
                          Редактировать
                        </button>
                        <button
                          type="button"
                          className="text-red-600 hover:underline"
                          onClick={() => deleteMutation.mutate(code.id)}
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
        <h3 className="text-sm font-semibold text-zinc-900">
          {editingId ? 'Редактирование промокода' : 'Новый промокод'}
        </h3>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Код</label>
              <input
                type="text"
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Тип скидки</label>
              <select
                value={form.discount_type}
                onChange={e =>
                  setForm({
                    ...form,
                    discount_type: e.target.value as 'percent' | 'fixed',
                  })
                }
                className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm"
              >
                <option value="percent">Процент</option>
                <option value="fixed">Фиксированная сумма</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Значение</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.discount_value}
                onChange={e => setForm({ ...form, discount_value: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Лимит использований</label>
              <input
                type="number"
                min={0}
                value={form.max_uses ?? ''}
                onChange={e =>
                  setForm({
                    ...form,
                    max_uses: e.target.value ? Number(e.target.value) : null,
                  })
                }
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Мин. сумма заказа</label>
              <input
                type="number"
                min={0}
                step="0.01"
                value={form.min_order_amount ?? ''}
                onChange={e => setForm({ ...form, min_order_amount: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600">
                <input
                  type="checkbox"
                  checked={form.is_active ?? false}
                  onChange={e => setForm({ ...form, is_active: e.target.checked })}
                />
                Активен
              </label>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата начала</label>
              <input
                type="datetime-local"
                value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="block text-xs font-medium text-zinc-500">Дата окончания</label>
              <input
                type="datetime-local"
                value={form.end_date}
                onChange={e => setForm({ ...form, end_date: e.target.value })}
                className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            {editingId && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEditingId(null);
                  setForm({
                    code: '',
                    discount_type: 'percent',
                    discount_value: '',
                    max_uses: null,
                    min_order_amount: '',
                    start_date: '',
                    end_date: '',
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
              {editingId ? 'Сохранить' : 'Создать промокод'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
