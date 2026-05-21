'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { checkStaffAccess, login } from '@/lib/api/services/auth.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useQueryClient } from '@tanstack/react-query';
import {
  AUTH_ME_QUERY_KEY,
  AUTH_STAFF_ACCESS_QUERY_KEY,
  authMeQueryFn,
} from '@/lib/hooks/useAuth';
import { BrandLogo } from '@/components/layout/BrandLogo';

function AdminLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const next = searchParams.get('next') ?? '/admin/orders';

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedPhone = phone.trim();
    if (!trimmedPhone) {
      setError('Введите номер телефона.');
      return;
    }
    if (!password) {
      setError('Введите пароль.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(trimmedPhone, password);
      await queryClient.fetchQuery({
        queryKey: AUTH_ME_QUERY_KEY,
        queryFn: authMeQueryFn,
      });
      await queryClient.invalidateQueries({ queryKey: AUTH_STAFF_ACCESS_QUERY_KEY });
      const allowed = await checkStaffAccess();
      if (!allowed) {
        setError('Доступ только для сотрудников.');
        return;
      }
      router.push(next);
    } catch (err: unknown) {
      const res = (err as { response?: { data?: Record<string, unknown>; status?: number } })
        ?.response;
      const data = res?.data;
      const status = res?.status;
      let msg = 'Неверный телефон или пароль.';
      if (data && typeof data === 'object') {
        if (typeof (data as { detail?: string }).detail === 'string') {
          msg = (data as { detail: string }).detail;
        }
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-100 px-4">
      <Card className="w-full max-w-md p-8">
        <div className="mb-4 flex justify-center">
          <BrandLogo href="/" height={60} />
        </div>
        <h1 className="mb-2 text-xl font-semibold text-zinc-900">Вход в админ-панель</h1>
        <p className="mb-6 text-sm text-zinc-500">Только для сотрудников.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-900">Телефон</label>
            <Input
              type="tel"
              placeholder="+7 (999) 123-45-67"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              autoComplete="tel"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-900">Пароль</label>
            <Input
              type="password"
              placeholder="Пароль"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" fullWidth loading={loading}>
            Войти
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-500">
          <Link href="/" className="text-zinc-900 underline hover:no-underline">
            Вернуться на сайт
          </Link>
        </p>
      </Card>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-zinc-100">
          <div className="h-64 w-80 animate-pulse rounded-xl bg-zinc-200" />
        </div>
      }
    >
      <AdminLoginContent />
    </Suspense>
  );
}
