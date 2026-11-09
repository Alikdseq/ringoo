'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import {
  applyOneCSync,
  dryRunOneCSync,
  getOneCSyncLogs,
  getOneCSyncStatus,
  probeOneCSync,
} from '@/lib/api/services/adminOnecSync.service';
import { getFriendlyErrorMessage } from '@/lib/errors';

export default function AdminOneCSyncPage() {
  const statusQuery = useQuery({
    queryKey: ['admin', 'onec-sync', 'status'],
    queryFn: getOneCSyncStatus,
    refetchInterval: 15_000,
  });
  const logsQuery = useQuery({
    queryKey: ['admin', 'onec-sync', 'logs'],
    queryFn: getOneCSyncLogs,
    refetchInterval: 15_000,
  });

  const refresh = () => {
    void statusQuery.refetch();
    void logsQuery.refetch();
  };

  const probe = useMutation({
    mutationFn: probeOneCSync,
    onSuccess: refresh,
  });
  const dryRun = useMutation({
    mutationFn: dryRunOneCSync,
    onSuccess: refresh,
  });
  const apply = useMutation({
    mutationFn: applyOneCSync,
    onSuccess: refresh,
  });

  const st = statusQuery.data;
  const busy = probe.isPending || dryRun.isPending || apply.isPending;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Синхронизация с 1С</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Каталог и остатки загружаются в базу Ringoo. Витрина и админка читают одни данные.
            Реальный apply — только при включённом API на согласованном контуре.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={refresh}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Обновить
        </Button>
      </div>

      {statusQuery.isLoading ? (
        <Loading />
      ) : statusQuery.isError ? (
        <p className="text-sm text-red-600">Не удалось загрузить статус синхронизации.</p>
      ) : st ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="space-y-2 p-4 text-sm">
            <h2 className="font-semibold text-zinc-900">Состояние</h2>
            <p>API 1С: {st.api_enabled ? 'включён' : 'выключен'}</p>
            <p>Периодический sync (Beat): {st.catalog_sync_enabled ? 'включён' : 'выключен'}</p>
            <p>Apply сейчас: {st.apply_running ? 'выполняется' : 'нет'}</p>
            <p>
              Возраст данных:{' '}
              {st.data_age_hours == null
                ? 'нет успешного apply'
                : `${st.data_age_hours} ч (порог ${st.stale_threshold_hours} ч)`}
            </p>
            {st.data_stale ? (
              <p className="rounded-md bg-amber-50 px-2 py-1 text-amber-800">
                Данные считаются устаревшими или отсутствуют — проверьте последний успешный импорт.
              </p>
            ) : (
              <p className="text-emerald-700">Данные в пределах порога актуальности.</p>
            )}
          </Card>
          <Card className="space-y-3 p-4 text-sm">
            <h2 className="font-semibold text-zinc-900">Действия</h2>
            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => probe.mutate()}>
                Проверить подключение
              </Button>
              <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => dryRun.mutate()}>
                Dry Run
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={busy || !st.api_enabled || st.apply_running}
                onClick={() => {
                  if (
                    !window.confirm(
                      'Запустить apply каталога из 1С? Изменятся категории/товары/остатки в Ringoo. 1С не изменится.'
                    )
                  ) {
                    return;
                  }
                  apply.mutate();
                }}
              >
                Запустить синхронизацию
              </Button>
            </div>
            {[probe, dryRun, apply].map((m, i) =>
              m.isError ? (
                <p key={i} className="text-red-600">
                  {getFriendlyErrorMessage(m.error)}
                </p>
              ) : null
            )}
            {dryRun.isSuccess ? (
              <pre className="max-h-40 overflow-auto rounded bg-zinc-50 p-2 text-xs">
                {JSON.stringify(dryRun.data, null, 2)}
              </pre>
            ) : null}
            {apply.isSuccess ? (
              <pre className="max-h-40 overflow-auto rounded bg-zinc-50 p-2 text-xs">
                {JSON.stringify(apply.data, null, 2)}
              </pre>
            ) : null}
          </Card>
        </div>
      ) : null}

      <Card className="overflow-x-auto p-0">
        <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">История запусков</div>
        {logsQuery.isLoading ? (
          <div className="p-6">
            <Loading />
          </div>
        ) : (
          <table className="w-full min-w-[800px] text-sm">
            <thead>
              <tr className="border-b bg-zinc-50 text-xs uppercase text-zinc-500">
                <th className="px-3 py-2 text-left">Run</th>
                <th className="px-3 py-2 text-left">Статус</th>
                <th className="px-3 py-2 text-left">Режим</th>
                <th className="px-3 py-2 text-left">Товары ±</th>
                <th className="px-3 py-2 text-left">Ошибки</th>
                <th className="px-3 py-2 text-left">Время</th>
              </tr>
            </thead>
            <tbody>
              {(logsQuery.data || []).map(row => (
                <tr key={row.id} className="border-b border-zinc-100">
                  <td className="px-3 py-2 font-mono text-xs">{row.run_id}</td>
                  <td className="px-3 py-2">{row.status}</td>
                  <td className="px-3 py-2">{row.dry_run ? 'dry-run' : 'apply'}</td>
                  <td className="px-3 py-2">
                    +{row.products_created} / ~{row.products_updated}
                  </td>
                  <td className="px-3 py-2">{row.errors_count}</td>
                  <td className="px-3 py-2 text-xs text-zinc-500">
                    {row.started_at ? new Date(row.started_at).toLocaleString('ru-RU') : '—'}
                    {row.duration_ms != null ? ` (${row.duration_ms} мс)` : ''}
                  </td>
                </tr>
              ))}
              {!logsQuery.data?.length ? (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-zinc-500">
                    Запусков пока нет
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
