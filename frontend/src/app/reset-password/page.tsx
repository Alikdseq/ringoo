'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { confirmPasswordReset } from '@/lib/api/services/auth.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { PageContainer } from '@/components/layout/PageContainer';
import { getFriendlyErrorMessage } from '@/lib/errors';

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const uid = (searchParams.get('uid') || '').trim();
  const token = (searchParams.get('token') || '').trim();

  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const linkInvalid = !uid || !token;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (linkInvalid) {
      setError('Ссылка восстановления неполная или повреждена.');
      return;
    }
    if (password.length < 8) {
      setError('Пароль должен быть не короче 8 символов.');
      return;
    }
    if (password !== password2) {
      setError('Пароли не совпадают.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await confirmPasswordReset({ uid, token, new_password: password });
      setDone(true);
      setTimeout(() => router.push('/login'), 1500);
    } catch (err) {
      setError(getFriendlyErrorMessage(err));
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
        <Link href="/login" className="hover:text-foreground">
          Вход
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Новый пароль</span>
      </nav>

      <Card className="p-6">
        <h1 className="mb-1 text-xl font-semibold text-foreground">Новый пароль</h1>
        <p className="mb-6 text-sm text-foreground-muted">
          Придумайте новый пароль для входа в личный кабинет.
        </p>

        {linkInvalid ? (
          <p className="text-sm text-danger">
            Ссылка недействительна. Запросите восстановление пароля ещё раз.
          </p>
        ) : done ? (
          <p className="text-sm text-foreground">
            Пароль обновлён. Перенаправляем на страницу входа…
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="reset-password-new"
                className="mb-2 block text-sm font-medium text-foreground"
              >
                Новый пароль
              </label>
              <Input
                id="reset-password-new"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="reset-password-confirm"
                className="mb-2 block text-sm font-medium text-foreground"
              >
                Повторите пароль
              </label>
              <Input
                id="reset-password-confirm"
                type="password"
                autoComplete="new-password"
                value={password2}
                onChange={e => setPassword2(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" fullWidth loading={loading}>
              Сохранить пароль
            </Button>
          </form>
        )}
      </Card>
    </PageContainer>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <PageContainer className="max-w-md py-12">
          <div className="h-8 w-48 animate-pulse rounded bg-zinc-200" />
          <div className="mt-6 h-64 animate-pulse rounded-xl bg-zinc-100" />
        </PageContainer>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
