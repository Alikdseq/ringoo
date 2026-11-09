import { apiClient } from '@/lib/api/client';

export type OneCSyncLog = {
  id: string;
  run_id: string;
  sync_type: string;
  source: string;
  status: string;
  dry_run: boolean;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  records_received: number;
  categories_created: number;
  categories_updated: number;
  products_created: number;
  products_updated: number;
  stocks_upserted: number;
  errors_count: number;
  error_messages: unknown;
  summary: Record<string, unknown>;
  celery_task_id?: string;
};

export type OneCSyncStatus = {
  api_enabled: boolean;
  catalog_sync_enabled: boolean;
  partner_sync_on_register: boolean;
  apply_running: boolean;
  last_success: OneCSyncLog | null;
  last_run: OneCSyncLog | null;
  data_age_hours: number | null;
  data_stale: boolean;
  stale_threshold_hours: number;
};

export async function getOneCSyncStatus(): Promise<OneCSyncStatus> {
  const { data } = await apiClient.get<OneCSyncStatus>('/admin/onec/sync/status/');
  return data;
}

export async function getOneCSyncLogs(): Promise<OneCSyncLog[]> {
  const { data } = await apiClient.get<OneCSyncLog[]>('/admin/onec/sync/logs/');
  return Array.isArray(data) ? data : [];
}

export async function probeOneCSync(): Promise<OneCSyncLog> {
  const { data } = await apiClient.post<OneCSyncLog>('/admin/onec/sync/probe/');
  return data;
}

export async function dryRunOneCSync(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post('/admin/onec/sync/dry-run/');
  return data as Record<string, unknown>;
}

export async function applyOneCSync(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post('/admin/onec/sync/apply/', { confirm: true });
  return data as Record<string, unknown>;
}
