'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { login } from '@/lib/api/services/auth.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useQueryClient } from '@tanstack/react-query';
import { AUTH_ME_QUERY_KEY, authMeQueryFn } from '@/lib/hooks/useAuth';
import { CART_QUERY_KEY } from '@/lib/hooks/useCart';
import { PageContainer } from '@/components/layout/PageContainer';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const next = searchParams.get('next') ?? '/profile';

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
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
      await login(trimmedPhone, password, rememberMe);
      await queryClient.fetchQuery({
        queryKey: AUTH_ME_QUERY_KEY,
        queryFn: authMeQueryFn,
      });
      await queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
      router.push(next);
    } catch (err: unknown) {
      const res = (err as { response?: { data?: Record<string, unknown>; status?: number } })
        ?.response;
      const data = res?.data;
      const status = res?.status;
      let msg = 'Неверный телефон или пароль.';
      if (status === 429) {
        const d =
          data && typeof data === 'object' && typeof (data as { detail?: string }).detail === 'string'
            ? (data as { detail: string }).detail
            : '';
        msg =
          d ||
          'Слишком много попыток входа. Подождите минуту и повторите. Если всё ещё 429 — в каталоге backend: python manage.py axes_reset (django-axes).';
      } else if (data && typeof data === 'object') {
        if (typeof (data as { detail?: string }).detail === 'string') {
          msg = (data as { detail: string }).detail;
        } else if (status === 400 && Array.isArray((data as { username?: string[] }).username)) {
          msg = (data as { username: string[] }).username[0] ?? msg;
        } else if (status === 400 && Array.isArray((data as { password?: string[] }).password)) {
          msg = (data as { password: string[] }).password[0] ?? msg;
        }
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer className="max-w-md py-12">
      <nav
        className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
        aria-label="Хлебные крошки"
      >
        <Link href="/" className="hover:text-foreground">
          Главная
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Вход</span>
      </nav>

      <Card className="p-6">
        <h1 className="mb-1 text-xl font-semibold text-foreground">Вход в личный кабинет</h1>
        <p className="mb-6 text-sm text-foreground-muted">Введите телефон и пароль.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Телефон</label>
            <Input
              type="tel"
              inputMode="tel"
              placeholder="+7 (999) 123-45-67"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              autoComplete="tel"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Пароль</label>
            <Input
              type="password"
              placeholder="Пароль"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground-muted">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={e => setRememberMe(e.target.checked)}
              className="size-4 rounded border-border text-brand focus:ring-brand"
            />
            Запомнить меня
          </label>
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" fullWidth loading={loading}>
            Войти
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-foreground-muted">
          Нет аккаунта?{' '}
          <Link href="/register" className="text-foreground underline hover:no-underline">
            Зарегистрироваться
          </Link>
        </p>
      </Card>
    </PageContainer>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <PageContainer className="max-w-md py-12">
          <div className="h-8 w-48 animate-pulse rounded bg-zinc-200" />
          <div className="mt-6 h-64 animate-pulse rounded-xl bg-zinc-100" />
        </PageContainer>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
