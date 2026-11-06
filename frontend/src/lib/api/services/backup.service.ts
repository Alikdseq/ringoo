import { apiClient } from '@/lib/api/client';

export interface BackupCreateResponse {
  id: string;
  status: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  encrypted: boolean;
  expires_at: string | null;
  download_token: string;
  manifest?: Record<string, unknown>;
}

export interface BackupStatusResponse {
  id: string;
  status: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  encrypted: boolean;
  expires_at: string | null;
  error_message?: string;
  downloadable: boolean;
  manifest?: Record<string, unknown>;
}

export async function createAdminBackup(password?: string): Promise<BackupCreateResponse> {
  const body = password ? { password } : {};
  const { data } = await apiClient.post<BackupCreateResponse>('/admin/backups/create/', body, {
    timeout: 600_000,
  });
  return data;
}

export async function getAdminBackupStatus(id: string): Promise<BackupStatusResponse> {
  const { data } = await apiClient.get<BackupStatusResponse>(`/admin/backups/${id}/`);
  return data;
}

/** Скачивание через авторизованный клиент (blob). */
export async function downloadAdminBackup(id: string, token: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/admin/backups/${id}/download/`, {
    params: { token },
    responseType: 'blob',
    timeout: 600_000,
  });
  return data;
}

export interface OffsiteStatusResponse {
  configured: boolean;
  s3_configured: boolean;
  encryption_configured: boolean;
  provider: string;
  connection_status?: string;
  bucket?: string | null;
  last_success_at?: string | null;
  last_success_size?: number | null;
  last_verified_at?: string | null;
  stored_count?: number;
  last_error?: string;
}

export async function getOffsiteStatus(): Promise<OffsiteStatusResponse> {
  const { data } = await apiClient.get<OffsiteStatusResponse>('/admin/backups/offsite/status/');
  return data;
}

export async function probeOffsite(): Promise<{ status: string; provider?: string; error?: string }> {
  const { data } = await apiClient.post('/admin/backups/offsite/probe/');
  return data;
}

export async function uploadOffsite(archiveId?: string): Promise<{ status: string; task_id?: string }> {
  const url = archiveId
    ? `/admin/backups/${archiveId}/offsite/upload/`
    : '/admin/backups/offsite/upload/';
  const { data } = await apiClient.post(url, {});
  return data;
}

export async function verifyOffsite(): Promise<{ status: string; detail?: string }> {
  const { data } = await apiClient.post('/admin/backups/offsite/verify/');
  return data;
}
