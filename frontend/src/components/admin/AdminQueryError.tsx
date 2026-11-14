'use client';

import type { ReactElement } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { getApiErrorStatus, getFriendlyErrorMessage } from '@/lib/errors';

/**
 * B8-007: явный error/not-found вместо вечного spinner при `!data`.
 */
export function AdminQueryError({
  error,
  resourceLabel,
  backHref,
  onRetry,
}: {
  error: unknown;
  resourceLabel: string;
  backHref?: string;
  onRetry?: () => void;
}): ReactElement {
  const status = getApiErrorStatus(error);
  const isNotFound = status === 404;
  const isForbidden = status === 403;
  const isUnauthorized = status === 401;

  let title = `Не удалось загрузить ${resourceLabel}`;
  if (isNotFound) title = `${resourceLabel} не найден(а)`;
  else if (isForbidden) title = 'Недостаточно прав';
  else if (isUnauthorized) title = 'Требуется вход';

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <p className="font-medium">{title}</p>
      <p className="mt-1">{getFriendlyErrorMessage(error)}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {onRetry && !isNotFound && !isUnauthorized ? (
          <Button type="button" size="sm" variant="outline" onClick={onRetry}>
            Повторить
          </Button>
        ) : null}
        {backHref ? (
          <Button asChild size="sm" variant="outline">
            <Link href={backHref}>Назад</Link>
          </Button>
        ) : null}
      </div>
    </div>
  );
}
