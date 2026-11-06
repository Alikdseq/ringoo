'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { HardDriveDownload, Shield } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { AUTH_STAFF_ACCESS_QUERY_KEY } from '@/lib/hooks/useAuth';
import { fetchStaffAccess } from '@/lib/api/services/auth.service';
import {
  createAdminBackup,
  downloadAdminBackup,
  getOffsiteStatus,
  probeOffsite,
  uploadOffsite,
  verifyOffsite,
  type BackupCreateResponse,
} from '@/lib/api/services/backup.service';
import { getFriendlyErrorMessage } from '@/lib/errors';

function formatBytes(n: number): string {
  if (!n || n < 0) return '0 Б';
  if (n < 1024) return `${n} Б`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} КБ`;
  return `${(n / (1024 * 1024)).toFixed(1)} МБ`;
}

export default function AdminBackupPage() {
  const { data: staffAccess } = useQuery({
    queryKey: AUTH_STAFF_ACCESS_QUERY_KEY,
    queryFn: () => fetchStaffAccess(),
  });
  const isSuperuser = Boolean(staffAccess?.is_superuser);
  const offsiteQuery = useQuery({
    queryKey: ['admin', 'backup', 'offsite'],
    queryFn: () => getOffsiteStatus(),
    enabled: isSuperuser,
  });
  const [password, setPassword] = useState('');
  const [useEncryption, setUseEncryption] = useState(true);
  const [busy, setBusy] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BackupCreateResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);

  async function handleCreate() {
    setError(null);
    setResult(null);
    setToken(null);
    if (!isSuperuser) {
      setError('Раздел доступен только суперпользователю.');
      return;
    }
    if (useEncryption && password.length < 8) {
      setError('Задайте пароль шифрования не короче 8 символов или отключите шифрование.');
      return;
    }
    setBusy(true);
    setStatusText('Создаём резервную копию (база + медиа). Это может занять несколько минут…');
    try {
      const data = await createAdminBackup(useEncryption ? password : undefined);
      setResult(data);
      setToken(data.download_token);
      setStatusText('Архив готов. Сохраните файл на компьютер и внешний носитель.');
      setPassword('');
    } catch (e) {
      setError(getFriendlyErrorMessage(e));
      setStatusText('');
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload() {
    if (!result || !token) return;
    setBusy(true);
    setError(null);
    try {
      const blob = await downloadAdminBackup(result.id, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename || 'ringoo_backup.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatusText(
        'Файл скачан. Скопируйте его на отключённый SSD/флешку. Пароль шифрования сервер не хранит.'
      );
    } catch (e) {
      setError(getFriendlyErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (!isSuperuser) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <Card className="p-6">
          <h1 className="text-xl font-semibold text-zinc-900">Резервное копирование</h1>
          <p className="mt-3 text-sm text-zinc-600">
            Создание полной резервной копии доступно только суперпользователю с подтверждённым
            доступом в админку.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900">Резервное копирование</h1>
        <p className="mt-2 text-sm text-zinc-600">
          Полный архив магазина: база данных, медиафайлы, манифест и инструкция по восстановлению.
          Секреты (.env, ключи) в архив не входят.
        </p>
      </div>

      <Card className="space-y-4 p-6">
        <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          <Shield className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            Архив содержит персональные данные клиентов. Храните его зашифрованным, минимум в двух
            независимых копиях; одну — на носителе, отключённом от компьютера. Пароль шифрования
            сервер не сохраняет и восстановить не сможет.
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm text-zinc-800">
          <input
            type="checkbox"
            checked={useEncryption}
            onChange={e => setUseEncryption(e.target.checked)}
            disabled={busy}
          />
          Шифровать архив паролем (AES-256-GCM)
        </label>

        {useEncryption ? (
          <div>
            <label className="block text-sm font-medium text-zinc-700" htmlFor="backup-password">
              Пароль шифрования
            </label>
            <input
              id="backup-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={busy}
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              placeholder="минимум 8 символов"
            />
          </div>
        ) : null}

        <Button
          type="button"
          onClick={handleCreate}
          disabled={busy}
          className="inline-flex w-full items-center justify-center gap-2 sm:w-auto"
        >
          <HardDriveDownload className="h-4 w-4" />
          {busy && !result ? 'Создание…' : 'Создать резервную копию и скачать'}
        </Button>

        {statusText ? <p className="text-sm text-zinc-700">{statusText}</p> : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        {result ? (
          <div className="space-y-3 rounded-lg border border-zinc-200 bg-zinc-50 p-4 text-sm">
            <p>
              <span className="font-medium">Файл:</span> {result.filename}
            </p>
            <p>
              <span className="font-medium">Размер:</span> {formatBytes(result.size_bytes)}
            </p>
            <p className="break-all">
              <span className="font-medium">SHA-256:</span> {result.sha256}
            </p>
            <p>
              <span className="font-medium">Шифрование:</span>{' '}
              {result.encrypted ? 'да' : 'нет'}
            </p>
            <Button type="button" onClick={handleDownload} disabled={busy || !token}>
              Скачать на компьютер
            </Button>
          </div>
        ) : null}
      </Card>

      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold text-zinc-900">Внешнее хранилище</h2>
        {offsiteQuery.data ? (
          <div className="space-y-1 text-sm text-zinc-700">
            <p>
              Статус:{' '}
              {offsiteQuery.data.configured
                ? offsiteQuery.data.connection_status || 'SUCCESS'
                : 'NOT_CONFIGURED'}
            </p>
            <p>Провайдер: {offsiteQuery.data.provider}</p>
            <p>
              Последняя успешная загрузка:{' '}
              {offsiteQuery.data.last_success_at
                ? String(offsiteQuery.data.last_success_at)
                : '—'}
            </p>
            <p>
              Размер последней копии:{' '}
              {formatBytes(Number(offsiteQuery.data.last_success_size || 0))}
            </p>
            <p>
              Проверка целостности:{' '}
              {offsiteQuery.data.last_verified_at
                ? String(offsiteQuery.data.last_verified_at)
                : '—'}
            </p>
            <p>Сохранённых копий: {offsiteQuery.data.stored_count ?? 0}</p>
            {offsiteQuery.data.last_error ? (
              <p className="text-red-600">Ошибка: {offsiteQuery.data.last_error}</p>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">Загрузка статуса…</p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                const r = await probeOffsite();
                setStatusText(`Проверка подключения: ${r.status}`);
                await offsiteQuery.refetch();
              } catch (e) {
                setError(getFriendlyErrorMessage(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Проверить подключение
          </Button>
          <Button
            type="button"
            disabled={busy || !result}
            onClick={async () => {
              if (!result) return;
              setBusy(true);
              setError(null);
              try {
                const r = await uploadOffsite(result.id);
                setStatusText(`Отправка во внешнее хранилище: ${r.status}`);
                await offsiteQuery.refetch();
              } catch (e) {
                setError(getFriendlyErrorMessage(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Отправить резервную копию во внешнее хранилище
          </Button>
          <Button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError(null);
              try {
                const r = await verifyOffsite();
                setStatusText(`Проверка последней копии: ${r.status}`);
                await offsiteQuery.refetch();
              } catch (e) {
                setError(getFriendlyErrorMessage(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Проверить последнюю копию
          </Button>
        </div>
        <p className="text-xs text-zinc-500">
          Секреты и ключи шифрования в интерфейсе не отображаются. Инструкция:{' '}
          docs/ops/OFFSITE_BACKUP_SETUP.md
        </p>
      </Card>

      <Card className="space-y-2 p-6 text-sm text-zinc-600">
        <h2 className="font-semibold text-zinc-900">После скачивания</h2>
        <ol className="list-decimal space-y-1 pl-5">
          <li>Сохраните файл на компьютер.</li>
          <li>Скопируйте на внешний SSD или флешку и отключите носитель.</li>
          <li>Запишите пароль шифрования отдельно (не в том же файле).</li>
          <li>Периодически проверяйте восстановление по инструкции в документации.</li>
        </ol>
      </Card>
    </div>
  );
}
