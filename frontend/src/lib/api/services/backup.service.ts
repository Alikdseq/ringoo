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
