'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useMutation, useQuery } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import {
  Clipboard,
  Loader2,
  PackageSearch,
  Phone,
  RefreshCcw,
  Truck,
  XCircle,
} from 'lucide-react';
import type { Order } from '@/types/api';
import { cancelOrder, checkOrderStatus, reorderOrder } from '@/lib/api/services/orders.service';
import { getStoreDetail } from '@/lib/api/services/stores.service';
import { useAuth } from '@/lib/hooks/useAuth';
import { copyToClipboard } from '@/lib/clipboard';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/theme/utils';

function normalizePhoneForApi(raw: string): string {
  const digits = (raw || '').replace(/\D+/g, '');
  if (!digits) return '';
  // РФ: 8XXXXXXXXXX -> 7XXXXXXXXXX
  let d = digits;
  if (d.length === 11 && d.startsWith('8')) d = `7${d.slice(1)}`;
  if (d.length === 10) d = `7${d}`;
  if (d.startsWith('7')) return `+${d}`;
  return `+${d}`;
}

function friendlyStatus(status: string): { label: string; tone: 'muted' | 'info' | 'warn' | 'ok' | 'danger' } {
  switch (status) {
    case 'new':
      return { label: 'В обработке', tone: 'muted' };
    case 'confirmed':
      return { label: 'Подтверждён', tone: 'info' };
    case 'in_progress':
      return { label: 'В доставке', tone: 'warn' };
    case 'completed':
      return { label: 'Выполнен', tone: 'ok' };
    case 'cancelled':
      return { label: 'Отменён', tone: 'danger' };
    default:
      return { label: status, tone: 'muted' };
  }
}

function StatusBadge({ status }: { status: string }) {
  const s = friendlyStatus(status);
  const cls =
    s.tone === 'ok'
      ? 'bg-emerald-50 text-emerald-700'
      : s.tone === 'danger'
        ? 'bg-red-50 text-red-700'
        : s.tone === 'warn'
          ? 'bg-amber-50 text-amber-700'
          : s.tone === 'info'
            ? 'bg-sky-50 text-sky-700'
            : 'bg-zinc-100 text-zinc-700';
  return <span className={cn('inline-flex rounded-full px-3 py-1 text-xs font-semibold', cls)}>{s.label}</span>;
}

function StatusProgress({ status }: { status: string }) {
  if (status === 'cancelled') return null;
  const steps: { key: string; label: string }[] = [
    { key: 'new', label: 'Оформлен' },
    { key: 'confirmed', label: 'Подтверждён' },
    { key: 'in_progress', label: 'В доставке' },
    { key: 'completed', label: 'Получен' },
  ];
  const idx = Math.max(0, steps.findIndex(s => s.key === status));
  return (
    <div className="mt-4">
      <div className="flex items-center justify-between gap-2">
        {steps.map((s, i) => {
          const active = i <= idx;
          return (
            <div key={s.key} className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    'h-2 w-2 shrink-0 rounded-full',
                    active ? 'bg-emerald-600' : 'bg-zinc-200'
                  )}
                  aria-hidden
                />
                <div className={cn('h-1 flex-1 rounded-full', active ? 'bg-emerald-600/60' : 'bg-zinc-200')} />
              </div>
              <div className={cn('mt-2 text-[11px] font-medium', active ? 'text-foreground' : 'text-foreground-muted')}>
                {s.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function money(v: string) {
  const n = Number(v);
  if (!Number.isFinite(n)) return v;
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatAddress(addr: Record<string, unknown> | null | undefined): string {
  if (!addr || typeof addr !== 'object') return '—';
  const a = addr as Record<string, string | null | undefined>;
  const parts = [
    a.city,
    [a.street, a.house].filter(Boolean).join(' '),
    a.apartment ? `кв. ${a.apartment}` : null,
    a.postal_code ? `индекс ${a.postal_code}` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(', ') : '—';
}

export function OrderStatusContent() {
  const { isAuthenticated, user } = useAuth();

  const [orderNumber, setOrderNumber] = useState('');
  const [phone, setPhone] = useState('');
  const [order, setOrder] = useState<Order | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !user?.phone?.trim()) return;
    setPhone(prev => (prev.trim() ? prev : user.phone.trim()));
  }, [isAuthenticated, user?.phone]);

  const canCancel = order?.status === 'new' || order?.status === 'confirmed';
  const canReorder = order?.status === 'completed' || order?.status === 'cancelled';

  const storeDetailQuery = useQuery({
    queryKey: ['stores', 'detail', order?.store],
    queryFn: () => getStoreDetail(order!.store as string),
    enabled: Boolean(order && order.delivery_type === 'pickup' && order.store),
    staleTime: 5 * 60 * 1000,
  });

  const checkMutation = useMutation({
    mutationFn: async () => {
      const num = orderNumber.trim();
      const ph = normalizePhoneForApi(phone);
      return await checkOrderStatus(num, ph);
    },
    retry: false,
    onSuccess: data => {
      setOrder(data);
      setNotFound(false);
    },
    onError: (e: unknown) => {
      setOrder(null);
      setNotFound(isAxiosError(e) && e.response?.status === 404);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!order) throw new Error('No order');
      const payload = isAuthenticated ? undefined : { order_number: order.order_number, phone: normalizePhoneForApi(phone) };
      return await cancelOrder(order.id, payload);
    },
    onSuccess: next => setOrder(next),
  });

  const reorderMutation = useMutation({
    mutationFn: async () => {
      if (!order) throw new Error('No order');
      return await reorderOrder(order.id);
    },
  });

  const submitDisabled = useMemo(() => {
    return !orderNumber.trim() || normalizePhoneForApi(phone).length < 8;
  }, [orderNumber, phone]);

  const helpText = 'Номер приходит на email и в SMS после оформления заказа.';

  const handleCopyOrderNumber = async (value: string) => {
    const ok = await copyToClipboard(value);
    setCopyFeedback(ok ? 'Номер скопирован' : 'Не удалось скопировать');
    window.setTimeout(() => setCopyFeedback(null), 2000);
  };

  return (
    <div className="bg-background">
      {/* HERO */}
      <section className="px-2 py-10 sm:px-4 sm:py-14 lg:px-6">
        <div className="mx-auto w-full max-w-4xl">
          <Card className="relative overflow-hidden rounded-[32px] border border-border bg-white p-6 sm:p-10">
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.10]"
              aria-hidden
              style={{
                backgroundImage:
                  'radial-gradient(circle at 12% 14%, rgba(46, 125, 50, 0.35), transparent 45%), radial-gradient(circle at 75% 35%, rgba(59, 130, 246, 0.16), transparent 45%)',
              }}
            />

            <div className="relative grid gap-6">
              <div>
                <p className="text-sm font-semibold text-brand">Самообслуживание</p>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">Где мой заказ?</h1>
                <p className="mt-3 text-base text-foreground-muted sm:text-lg">
                  Введите номер заказа и телефон — покажем статус и детали.
                </p>
              </div>

              <form
                onSubmit={e => {
                  e.preventDefault();
                  if (submitDisabled) return;
                  checkMutation.mutate();
                }}
                className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
              >
                <div>
                  <label htmlFor="order-number" className="mb-1 block text-sm text-foreground-muted">
                    Номер заказа
                  </label>
                  <div className="flex gap-2">
                    <Input
                      id="order-number"
                      value={orderNumber}
                      onChange={e => setOrderNumber(e.target.value)}
                      placeholder="Например, ORD-20260329-a1a5cc"
                      autoComplete="off"
                      className="min-w-0 flex-1"
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="shrink-0 px-3"
                      disabled={!orderNumber.trim()}
                      aria-label="Скопировать номер заказа"
                      onClick={() => void handleCopyOrderNumber(orderNumber.trim())}
                    >
                      <Clipboard className="h-4 w-4" />
                    </Button>
                  </div>
                  {copyFeedback ? (
                    <p className="mt-1 text-xs text-brand" role="status">
                      {copyFeedback}
                    </p>
                  ) : null}
                </div>
                <div>
                  <label htmlFor="order-phone" className="mb-1 block text-sm text-foreground-muted">
                    Телефон
                  </label>
                  <div className="relative">
                    <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-muted" />
                    <Input
                      id="order-phone"
                      value={phone}
                      onChange={e => setPhone(e.target.value)}
                      placeholder="+7 918 702 09 11"
                      inputMode="tel"
                      className="pl-10"
                      autoComplete="tel"
                    />
                  </div>
                </div>
                <div className="flex items-end">
                  <Button type="submit" disabled={submitDisabled || checkMutation.isPending} className="w-full">
                    {checkMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Проверяем…
                      </>
                    ) : (
                      <>
                        Проверить <PackageSearch className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </form>

              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-foreground-muted">
                <button
                  type="button"
                  className="inline-flex items-center gap-2 hover:text-foreground"
                  onClick={() => alert(helpText)}
                >
                  Где найти номер заказа?
                </button>
                <Link href="/profile" className="hover:text-foreground">
                  Если вы авторизованы — заказы в профиле →
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* РЕЗУЛЬТАТ */}
      <section className="px-2 pb-12 sm:px-4 lg:px-6">
        <div className="mx-auto w-full max-w-4xl">
          {order && (
            <Card className="rounded-3xl border border-border bg-white p-6 sm:p-8">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="text-xs font-semibold text-foreground-muted">Заказ</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xl font-semibold text-foreground">
                      {order.order_number}
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="h-9 gap-1.5 px-3"
                      onClick={() => void handleCopyOrderNumber(order.order_number)}
                    >
                      <Clipboard className="h-4 w-4" />
                      Скопировать
                    </Button>
                  </div>
                  <div className="mt-2 text-sm text-foreground-muted">
                    {new Date(order.created_at).toLocaleString('ru-RU')}
                  </div>
                </div>
                <StatusBadge status={order.status} />
              </div>

              <StatusProgress status={order.status} />

              {/* Товары */}
              <div className="mt-8">
                <h2 className="text-sm font-semibold text-foreground-muted">Товары в заказе</h2>
                <div className="mt-3 overflow-hidden rounded-2xl border border-border">
                  <ul className="divide-y divide-border">
                    {order.items.map(it => (
                      <li key={it.id} className="grid gap-2 p-4 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-foreground">{it.product_title}</div>
                          <div className="mt-1 text-xs text-foreground-muted">Кол-во: {it.quantity}</div>
                        </div>
                        <div className="text-sm font-semibold text-foreground">
                          {money(it.item_total)} ₽
                          <div className="mt-1 text-xs font-medium text-foreground-muted">
                            {money(it.price)} ₽ / шт
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="mt-3 flex items-center justify-between text-sm">
                  <span className="text-foreground-muted">Итого</span>
                  <span className="text-base font-semibold text-foreground">{money(order.total_amount)} ₽</span>
                </div>
              </div>

              {/* Доставка и оплата */}
              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-border bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Truck className="h-4 w-4" /> Доставка
                  </div>
                  <div className="mt-2 text-sm text-foreground-muted">
                    {order.delivery_type === 'pickup'
                      ? 'Самовывоз'
                      : 'Курьером по адресу'}
                  </div>
                  <div className="mt-2 text-sm text-foreground">
                    {order.delivery_type === 'pickup'
                      ? storeDetailQuery.data
                        ? `Магазин: ${storeDetailQuery.data.name} (${storeDetailQuery.data.city}, ${storeDetailQuery.data.address})`
                        : order.store
                          ? 'Магазин: загрузка…'
                          : 'Магазин: —'
                      : `Адрес: ${formatAddress(order.delivery_address)}`}
                  </div>
                </div>

                <div className="rounded-2xl border border-border bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Clipboard className="h-4 w-4" /> Оплата
                  </div>
                  <div className="mt-2 text-sm text-foreground-muted">Способ: {order.payment_type}</div>
                  <div className="mt-2 text-sm text-foreground-muted">
                    Доставка: {money(order.delivery_cost)} ₽
                  </div>
                </div>
              </div>

              {/* Бонусы */}
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-border bg-white p-4">
                  <div className="text-sm font-semibold text-foreground">Бонусы</div>
                  <div className="mt-2 text-sm text-foreground-muted">Потрачено: −{money(order.bonus_used)} </div>
                  <div className="mt-1 text-sm text-foreground-muted">Начислено: +{money(order.bonus_earned)} </div>
                </div>
                <div className="rounded-2xl border border-border bg-white p-4">
                  <div className="text-sm font-semibold text-foreground">Действия</div>
                  <div className="mt-3 grid gap-2">
                    {canReorder && (
                      isAuthenticated ? (
                        <Button
                          type="button"
                          variant="outline"
                          loading={reorderMutation.isPending}
                          onClick={async () => {
                            await reorderMutation.mutateAsync();
                            window.location.href = '/cart';
                          }}
                        >
                          Повторить заказ <RefreshCcw className="ml-2 h-4 w-4" />
                        </Button>
                      ) : (
                        <Button asChild variant="outline">
                          <Link href={`/login?next=${encodeURIComponent('/order-status')}`}>
                            Войти, чтобы повторить заказ
                          </Link>
                        </Button>
                      )
                    )}
                    {canCancel && (
                      <Button
                        type="button"
                        variant="secondary"
                        loading={cancelMutation.isPending}
                        onClick={() => {
                          const ok = confirm('Отменить заказ? Вернуть заказ будет нельзя.');
                          if (!ok) return;
                          cancelMutation.mutate();
                        }}
                      >
                        Отменить заказ <XCircle className="ml-2 h-4 w-4" />
                      </Button>
                    )}
                    <Button asChild variant="ghost">
                      <a
                        href={`https://wa.me/79184157788?text=${encodeURIComponent(`Здравствуйте! Вопрос по заказу ${order.order_number}`)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Написать в поддержку
                      </a>
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {notFound && (
            <Card className="rounded-3xl border border-border bg-white p-8 text-center">
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-zinc-100 text-zinc-700">
                <span className="text-xl">?</span>
              </div>
              <h2 className="text-lg font-semibold text-foreground">Заказ не найден</h2>
              <p className="mt-2 text-sm text-foreground-muted">
                Проверьте правильность номера и телефона. Если вы оформляли заказ как гость, используйте тот же номер
                телефона, что указывали при оформлении.
              </p>
              <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
                <Button
                  type="button"
                  onClick={() => {
                    setOrder(null);
                    setNotFound(false);
                    setOrderNumber('');
                    setPhone('');
                  }}
                >
                  Попробовать снова
                </Button>
                <Button asChild variant="outline">
                  <a href="https://wa.me/79184157788" target="_blank" rel="noopener noreferrer">
                    Связаться с поддержкой
                  </a>
                </Button>
              </div>
            </Card>
          )}
        </div>
      </section>
    </div>
  );
}

