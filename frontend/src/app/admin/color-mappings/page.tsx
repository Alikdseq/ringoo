'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import {
  getColorMappings,
  updateColorMapping,
  type ColorMappingRow,
} from '@/lib/api/services/adminColorMappings.service';
import { getFriendlyErrorMessage } from '@/lib/errors';

const STATUSES = ['unmapped', 'matched', 'conflict', 'ignored'] as const;

export default function AdminColorMappingsPage() {
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('');
  const [drafts, setDrafts] = useState<Record<string, Partial<ColorMappingRow>>>({});

  const { data = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['admin', 'color-mappings', q, status],
    queryFn: () =>
      getColorMappings({
        q: q.trim() || undefined,
        mapping_status: status || undefined,
      }),
  });

  const save = useMutation({
    mutationFn: (row: ColorMappingRow) => {
      const d = drafts[row.id] || {};
      return updateColorMapping(row.id, {
        onec_code: d.onec_code ?? row.onec_code,
        onec_characteristic_ref: d.onec_characteristic_ref ?? row.onec_characteristic_ref,
        mapping_status: d.mapping_status ?? row.mapping_status,
        sku: d.sku ?? row.sku,
      });
    },
    onSuccess: () => {
      setDrafts({});
      void refetch();
    },
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Сопоставление цветов ↔ 1С</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Не угадываем GUID по названию. Указывайте только подтверждённый код характеристики из
          выгрузки 1С. Без кода статус matched недоступен.
        </p>
      </div>

      <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-1">
          <label className="text-xs font-medium text-zinc-500">Поиск</label>
          <input
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Товар, цвет, код…"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-zinc-500">Статус</label>
          <select
            className="rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            value={status}
            onChange={e => setStatus(e.target.value)}
          >
            <option value="">Все</option>
            {STATUSES.map(s => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => refetch()}>
          Обновить
        </Button>
      </Card>

      {isLoading ? (
        <Loading />
      ) : isError ? (
        <p className="text-sm text-red-600">Не удалось загрузить сопоставления.</p>
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[960px] text-sm">
            <thead>
              <tr className="border-b bg-zinc-50 text-xs uppercase text-zinc-500">
                <th className="px-3 py-2 text-left">Товар</th>
                <th className="px-3 py-2 text-left">Цвет Ringoo</th>
                <th className="px-3 py-2 text-left">Код 1С варианта</th>
                <th className="px-3 py-2 text-left">Характеристика</th>
                <th className="px-3 py-2 text-left">Статус</th>
                <th className="px-3 py-2 text-right">Сохранить</th>
              </tr>
            </thead>
            <tbody>
              {data.map(row => {
                const d = drafts[row.id] || {};
                return (
                  <tr key={row.id} className="border-b border-zinc-100">
                    <td className="px-3 py-2">
                      <div className="font-medium">{row.product_title}</div>
                      <div className="font-mono text-[10px] text-zinc-400">
                        {row.product_onec_code || 'без onec_code'}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {row.label}{' '}
                      <span className="text-xs text-zinc-400">({row.slug})</span>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="w-full rounded border border-zinc-200 px-2 py-1 font-mono text-xs"
                        value={d.onec_code ?? row.onec_code ?? ''}
                        onChange={e =>
                          setDrafts(prev => ({
                            ...prev,
                            [row.id]: { ...prev[row.id], onec_code: e.target.value },
                          }))
                        }
                        placeholder="Только из выгрузки 1С"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="w-full rounded border border-zinc-200 px-2 py-1 font-mono text-xs"
                        value={
                          d.onec_characteristic_ref ?? row.onec_characteristic_ref ?? ''
                        }
                        onChange={e =>
                          setDrafts(prev => ({
                            ...prev,
                            [row.id]: {
                              ...prev[row.id],
                              onec_characteristic_ref: e.target.value,
                            },
                          }))
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="rounded border border-zinc-200 px-2 py-1 text-xs"
                        value={d.mapping_status ?? row.mapping_status}
                        onChange={e =>
                          setDrafts(prev => ({
                            ...prev,
                            [row.id]: { ...prev[row.id], mapping_status: e.target.value },
                          }))
                        }
                      >
                        {STATUSES.map(s => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        loading={save.isPending}
                        onClick={() => save.mutate(row)}
                      >
                        OK
                      </Button>
                    </td>
                  </tr>
                );
              })}
              {!data.length ? (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-zinc-500">
                    Нет строк
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          {save.isError ? (
            <p className="p-3 text-sm text-red-600">{getFriendlyErrorMessage(save.error)}</p>
          ) : null}
        </Card>
      )}
    </div>
  );
}
