'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { register } from '@/lib/api/services/auth.service';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useQueryClient } from '@tanstack/react-query';
import { AUTH_ME_QUERY_KEY, authMeQueryFn } from '@/lib/hooks/useAuth';
import { CART_QUERY_KEY } from '@/lib/hooks/useCart';
import { ConsentCheckboxes } from '@/components/legal/ConsentCheckboxes';
import { PageContainer } from '@/components/layout/PageContainer';

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const next = searchParams.get('next') ?? '/profile';

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [lastName, setLastName] = useState('');
  const [firstName, setFirstName] = useState('');
  const [middleName, setMiddleName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [consentPersonal, setConsentPersonal] = useState(false);
  const [consentOffer, setConsentOffer] = useState(false);
  const [consentMarketing, setConsentMarketing] = useState(false);

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
    if (password.length < 8) {
      setError('Пароль должен быть не менее 8 символов.');
      return;
    }
    if (password !== passwordConfirm) {
      setError('Пароли не совпадают.');
      return;
    }
    if (!consentPersonal) {
      setError('Подтвердите согласие на обработку персональных данных.');
      return;
    }
    if (!consentOffer) {
      setError('Подтвердите принятие публичной оферты.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await register({
        phone: trimmedPhone,
        password,
        last_name: lastName.trim() || undefined,
        first_name: firstName.trim() || undefined,
        middle_name: middleName.trim() || undefined,
        consent_personal_data: true,
        consent_offer: true,
        consent_marketing: consentMarketing,
      });
      await queryClient.fetchQuery({
        queryKey: AUTH_ME_QUERY_KEY,
        queryFn: authMeQueryFn,
      });
      await queryClient.invalidateQueries({ queryKey: CART_QUERY_KEY });
      router.push(next);
    } catch (err: unknown) {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const detail = typeof data?.detail === 'string' ? data.detail : undefined;
      const phoneError = Array.isArray(data?.phone) ? data.phone[0] : undefined;
      setError(
        detail ??
          (typeof phoneError === 'string' ? phoneError : 'Ошибка регистрации. Попробуйте снова.')
      );
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
        <span className="text-foreground">Регистрация</span>
      </nav>

      <Card className="p-6">
        <h1 className="mb-1 text-xl font-semibold text-foreground">Регистрация</h1>
        <p className="mb-6 text-sm text-foreground-muted">
          Телефон будет логином для входа. Заполните пароль и ФИО.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Телефон <span className="text-danger">*</span>
            </label>
            <Input
              type="tel"
              placeholder="+7 (999) 123-45-67"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              autoComplete="tel"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Пароль <span className="text-danger">*</span>
            </label>
            <Input
              type="password"
              placeholder="Не менее 8 символов"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Повторите пароль <span className="text-danger">*</span>
            </label>
            <Input
              type="password"
              placeholder="Повторите пароль"
              value={passwordConfirm}
              onChange={e => setPasswordConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Фамилия</label>
            <Input
              type="text"
              placeholder="Иванов"
              value={lastName}
              onChange={e => setLastName(e.target.value)}
              autoComplete="family-name"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Имя</label>
            <Input
              type="text"
              placeholder="Иван"
              value={firstName}
              onChange={e => setFirstName(e.target.value)}
              autoComplete="given-name"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Отчество</label>
            <Input
              type="text"
              placeholder="Иванович"
              value={middleName}
              onChange={e => setMiddleName(e.target.value)}
              autoComplete="additional-name"
            />
          </div>
          <ConsentCheckboxes
            consentPersonal={consentPersonal}
            onConsentPersonalChange={setConsentPersonal}
            consentOffer={consentOffer}
            onConsentOfferChange={setConsentOffer}
            consentMarketing={consentMarketing}
            onConsentMarketingChange={setConsentMarketing}
            showOffer
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <Button type="submit" fullWidth loading={loading}>
            Зарегистрироваться
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-foreground-muted">
          Уже есть аккаунт?{' '}
          <Link href="/login" className="text-foreground underline hover:no-underline">
            Войти
          </Link>
        </p>
      </Card>
    </PageContainer>
  );
}

export default function RegisterPage() {
  return (
    <Suspense
      fallback={
        <PageContainer className="max-w-md py-12">
          <div className="h-8 w-48 animate-pulse rounded bg-zinc-200" />
          <div className="mt-6 h-64 animate-pulse rounded-xl bg-zinc-100" />
        </PageContainer>
      }
    >
      <RegisterContent />
    </Suspense>
  );
}
