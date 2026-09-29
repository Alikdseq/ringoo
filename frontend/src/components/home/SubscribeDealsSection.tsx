'use client';

import { useMemo, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/theme/utils';
import { HOME_SECTION_CLASS, HOME_SECTION_INNER_CLASS } from '@/lib/theme/spacing';
import { useAuth, AUTH_ME_QUERY_KEY } from '@/lib/hooks/useAuth';
import { updateMarketingOptIn } from '@/lib/api/services/auth.service';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';

function isLikelyEmail(value: string): boolean {
  return value.includes('@') && value.includes('.');
}

function isLikelyPhone(value: string): boolean {
  const digits = value.replace(/\D/g, '');
  return digits.length >= 10;
}

export function SubscribeDealsSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const ringik = useRingikIntersectionTrigger(sectionRef, 'home_subscribe_phone');
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [value, setValue] = useState('');
  const [status, setStatus] = useState<'idle' | 'success'>('idle');
  const [error, setError] = useState<string | null>(null);

  const trimmed = value.trim();
  const isValid = useMemo(() => {
    if (!trimmed) return false;
    return isLikelyEmail(trimmed) || isLikelyPhone(trimmed);
  }, [trimmed]);

  const marketingMutation = useMutation({
    mutationFn: () => updateMarketingOptIn(true),
    onSuccess: next => {
      queryClient.setQueryData(AUTH_ME_QUERY_KEY, next);
    },
  });

  const onSubmit = async () => {
    setError(null);
    if (!isValid) {
      setError('Введите телефон или email.');
      return;
    }
    // Если пользователь авторизован — фиксируем согласие на рассылку на сервере.
    if (isAuthenticated) {
      try {
        await marketingMutation.mutateAsync();
      } catch {
        setError('Не удалось сохранить подписку. Попробуйте позже.');
        return;
      }
    }
    setStatus('success');
  };

  return (
    <section ref={sectionRef} className={cn('relative', HOME_SECTION_CLASS)}>
      <div className={HOME_SECTION_INNER_CLASS}>
        <Card className="relative overflow-visible rounded-[32px] border border-border bg-white p-6 sm:p-10">
          <div
            className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-[--color-brand-soft] blur-2xl"
            aria-hidden
          />

          <div className="relative grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                Подписка на акции
              </h2>
              <p className="mt-2 text-base text-foreground-muted sm:text-lg">
                Узнавай о скидках первым.
              </p>
              <p className="mt-2 text-sm text-foreground-muted">
                Можно указать телефон или email. Никакого спама — только важные скидки.
              </p>
            </div>

            <div>
              {status === 'success' ? (
                <div className="rounded-2xl border border-border bg-zinc-50 px-5 py-5">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-6 w-6 text-brand" />
                    <div>
                      <p className="font-semibold text-foreground">Готово!</p>
                      <p className="mt-1 text-sm text-foreground-muted">
                        Спасибо. Скоро пришлём лучшие предложения.
                      </p>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        className="mt-4"
                        onClick={() => {
                          setValue('');
                          setStatus('idle');
                        }}
                      >
                        Подписать ещё контакт
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="relative flex flex-col gap-2 sm:flex-row">
                    <Input
                      type="text"
                      placeholder="Телефон или email"
                      value={value}
                      onChange={e => setValue(e.target.value)}
                      className={cn('w-full', error && 'border-danger focus-visible:ring-danger')}
                      onKeyDown={e => e.key === 'Enter' && onSubmit()}
                      aria-label="Телефон или email"
                    />
                    <Button
                      type="button"
                      className="w-full sm:w-auto"
                      onClick={onSubmit}
                      disabled={!isValid || marketingMutation.isPending}
                      loading={marketingMutation.isPending}
                    >
                      Узнавать первым <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>

                    <Ringik
                      pose="phone"
                      placement="absolute"
                      visible={ringik.visible}
                      showMessage={ringik.showMessage}
                      message="Оставь контакт — пришлём лучшие акции"
                      className="-left-24 top-1/2 -translate-y-1/2 hidden sm:block z-[96]"
                    />
                  </div>
                  {error && <p className="text-sm text-danger">{error}</p>}
                  {!isAuthenticated && (
                    <p className="text-xs text-foreground-muted">
                      Подписка сохранится на устройстве. Чтобы привязать к аккаунту — войдите в профиль.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

