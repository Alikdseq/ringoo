'use client';

import { useState } from 'react';
import Link from 'next/link';
import { requestPasswordReset } from '@/lib/api/services/auth.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { PageContainer } from '@/components/layout/PageContainer';
import { getFriendlyErrorMessage } from '@/lib/errors';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [detail, setDetail] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes('@')) {
      setError('Введите корректный email.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const res = await requestPasswordReset(trimmed);
      setDetail(res.detail);
      setDone(true);
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
        <span className="text-foreground">Восстановление</span>
      </nav>

      <Card className="p-6">
        <h1 className="mb-1 text-xl font-semibold text-foreground">Забыли пароль?</h1>
        <p className="mb-6 text-sm text-foreground-muted">
          Укажите email, привязанный к аккаунту. Мы отправим ссылку для смены пароля, если
          аккаунт найден.
        </p>

        {done ? (
          <div className="space-y-4">
            <p className="text-sm text-foreground">{detail}</p>
            <Link href="/login" className="text-sm text-foreground underline hover:no-underline">
              Вернуться ко входу
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="forgot-password-email"
                className="mb-2 block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <Input
                id="forgot-password-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-danger">{error}</p>}
            <Button type="submit" fullWidth loading={loading}>
              Отправить ссылку
            </Button>
          </form>
        )}
      </Card>
    </PageContainer>
  );
}
