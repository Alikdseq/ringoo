'use client';

import { useEffect, useMemo, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Bell,
  Copy,
  Download,
  Heart,
  LayoutDashboard,
  LogOut,
  MapPin,
  Package,
  Star,
  Trash2,
  User as UserIcon,
} from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getOrders, getRatingsSummary } from '@/lib/api/services/orders.service';
import {
  deleteAccount,
  exportMyData,
  updateMarketingOptIn,
} from '@/lib/api/services/auth.service';
import { getAddresses } from '@/lib/api/services/addresses.service';
import { getWishlist } from '@/lib/api/services/wishlist.service';
import { addToCart } from '@/lib/api/services/cart.service';
import { copyToClipboard } from '@/lib/clipboard';
import { useAuth, AUTH_ME_QUERY_KEY, AUTH_STAFF_ACCESS_QUERY_KEY } from '@/lib/hooks/useAuth';
import { checkStaffAccess } from '@/lib/api/services/auth.service';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { Modal } from '@/components/ui/Modal';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import type { Order } from '@/types/api';
import { cn } from '@/lib/theme/utils';
import { formatRuDateShort } from '@/lib/format-date';

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  confirmed: 'Подтверждён',
  in_progress: 'В работе',
  completed: 'Выполнен',
  cancelled: 'Отменён',
};

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'new':
      return 'bg-zinc-100 text-zinc-700';
    case 'confirmed':
      return 'bg-sky-50 text-sky-700';
    case 'in_progress':
      return 'bg-amber-50 text-amber-800';
    case 'completed':
      return 'bg-emerald-50 text-emerald-700';
    case 'cancelled':
      return 'bg-red-50 text-red-700';
    default:
      return 'bg-zinc-100 text-zinc-700';
  }
}

function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const base = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
  return `${base}${path.startsWith('/') ? '' : '/'}${path}`;
}

function money(v: string) {
  const n = Number(v);
  if (!Number.isFinite(n)) return v;
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function productThumb(product: { title: string; images?: { image: string; is_main: boolean }[] }) {
  const main = product.images?.find(i => i.is_main) ?? product.images?.[0];
  return main?.image ?? null;
}

export function ProfileContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const [privacyError, setPrivacyError] = useState('');
  const [logoutOpen, setLogoutOpen] = useState(false);
  const [wishlistMsg, setWishlistMsg] = useState('');

  const marketingMutation = useMutation({
    mutationFn: updateMarketingOptIn,
    onSuccess: next => {
      queryClient.setQueryData(AUTH_ME_QUERY_KEY, next);
      setPrivacyError('');
    },
    onError: () => {
      setPrivacyError('Не удалось сохранить настройки рассылки.');
    },
  });

  const exportMutation = useMutation({
    mutationFn: exportMyData,
    onSuccess: data => {
      setPrivacyError('');
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json;charset=utf-8',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ringoo-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onError: () => {
      setPrivacyError('Не удалось выгрузить данные.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
  });

  const { data: ordersData } = useQuery({
    queryKey: ['orders'],
    queryFn: () => getOrders(),
    enabled: isAuthenticated,
  });

  const { data: isStaff = false } = useQuery({
    queryKey: AUTH_STAFF_ACCESS_QUERY_KEY,
    queryFn: () => checkStaffAccess(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const { data: ratingsSummary } = useQuery({
    queryKey: ['ratings-summary'],
    queryFn: getRatingsSummary,
  });

  const { data: addresses = [], isLoading: addressesLoading } = useQuery({
    queryKey: ['addresses'],
    queryFn: getAddresses,
    enabled: isAuthenticated,
  });

  const { data: wishlist = [], isLoading: wishlistLoading } = useQuery({
    queryKey: ['wishlist'],
    queryFn: getWishlist,
    enabled: isAuthenticated,
  });

  const addToCartMutation = useMutation({
    mutationFn: (productId: string) => addToCart(productId, 1),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
      setWishlistMsg('Товар добавлен в корзину.');
    },
    onError: (e: unknown) => {
      setWishlistMsg(getFriendlyErrorMessage(e));
    },
  });

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent('/profile')}`);
    }
  }, [isLoading, isAuthenticated, router]);

  const orders = ordersData?.results ?? [];
  const lastOrder: Order | undefined = orders[0];
  const ordersToRate = orders.filter(o => !o.has_rating && o.status !== 'cancelled');

  const defaultAddress = useMemo(() => {
    const def = addresses.find(a => a.is_default);
    return def ?? addresses[0];
  }, [addresses]);

  const wishlistPreview = useMemo(() => wishlist.slice(0, 4), [wishlist]);

  const displayName =
    user?.profile?.first_name || user?.profile?.last_name || user?.phone || 'Пользователь';

  const avatarSrc = mediaUrl(user?.profile?.avatar ?? null);

  const [orderCopyFeedback, setOrderCopyFeedback] = useState<string | null>(null);

  const copyPhone = async () => {
    if (!user?.phone) return;
    try {
      await navigator.clipboard.writeText(user.phone);
    } catch {
      /* ignore */
    }
  };

  const copyOrderNumber = async (orderNumber: string) => {
    const ok = await copyToClipboard(orderNumber);
    setOrderCopyFeedback(ok ? 'Номер скопирован' : 'Не удалось скопировать');
    window.setTimeout(() => setOrderCopyFeedback(null), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  const navTiles = [
    {
      href: '/orders',
      label: 'Мои заказы',
      desc: 'История, статусы, повтор заказа',
      icon: Package,
    },
    {
      href: '/wishlist',
      label: 'Избранное',
      desc: 'Отложенные товары',
      icon: Heart,
    },
    {
      href: '/profile/addresses',
      label: 'Адреса доставки',
      desc: 'Добавить и редактировать',
      icon: MapPin,
    },
    {
      href: '#bonuses',
      label: 'Бонусы',
      desc: 'Баланс и правила (скоро)',
      icon: Star,
    },
    {
      href: '#notifications',
      label: 'Уведомления',
      desc: 'Email и рассылка',
      icon: Bell,
    },
  ];

  return (
    <div className="bg-background">
      <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <nav
          className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
          aria-label="Хлебные крошки"
        >
          <Link href="/" className="hover:text-foreground">
            Главная
          </Link>
          <span aria-hidden>/</span>
          <span className="text-foreground">Профиль</span>
        </nav>

        {/* Блок 1: Hero */}
        <Card className="mb-6 overflow-hidden rounded-2xl border border-border p-6 shadow-sm sm:p-8">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
            <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-full bg-zinc-100 ring-2 ring-black/5">
              {avatarSrc ? (
                <Image src={avatarSrc} alt="" fill className="object-cover" sizes="80px" unoptimized />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-zinc-500">
                  <UserIcon className="h-9 w-9" />
                </div>
              )}
            </div>
            <div className="min-w-0 flex-1 text-center sm:text-left">
              <h1 className="text-2xl font-semibold text-foreground">Привет, {displayName}</h1>
              <div className="mt-2 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                <span className="text-sm text-foreground-muted">{user.phone}</span>
                <Button type="button" variant="ghost" size="sm" onClick={copyPhone} className="h-8 gap-1 px-2">
                  <Copy className="h-3.5 w-3.5" />
                  Копировать
                </Button>
              </div>
              {user.email && (
                <p className="mt-1 text-sm text-foreground-muted">{user.email}</p>
              )}
              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <Button asChild variant="outline" size="sm">
                  <Link href="#privacy">Управление данными</Link>
                </Button>
              </div>
            </div>
            <div id="bonuses" className="w-full shrink-0 rounded-2xl border border-amber-200 bg-amber-50/60 p-4 sm:w-56">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-900/80">Бонусы</p>
              <p className="mt-1 text-sm text-amber-950/90">
                Программа лояльности подключается на стороне сервера. Следите за новостями — скоро здесь
                появится баланс и история начислений.
              </p>
            </div>
          </div>
        </Card>

        {/* Блок 2: Навигация */}
        <section aria-labelledby="profile-nav-heading">
          <h2 id="profile-nav-heading" className="mb-3 text-lg font-semibold text-foreground">
            Личный кабинет
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {isStaff && (
              <Link
                href="/admin/orders"
                className="group flex gap-4 rounded-2xl border border-emerald-600/40 bg-emerald-50/50 p-4 shadow-sm transition-colors hover:border-emerald-600 hover:bg-emerald-50"
              >
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-600 text-white">
                  <LayoutDashboard className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-foreground">Админ-панель (ERP)</p>
                  <p className="mt-0.5 text-sm text-foreground-muted">Заказы, товары, менеджеры</p>
                </div>
              </Link>
            )}
            {navTiles.map(({ href, label, desc, icon: Icon }) => (
              <Link
                key={label}
                href={href}
                className="group flex gap-4 rounded-2xl border border-border bg-white p-4 shadow-sm transition-colors hover:border-emerald-600/30 hover:bg-emerald-50/30"
              >
                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-zinc-100 text-zinc-700 group-hover:bg-white">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-foreground">{label}</p>
                  <p className="mt-0.5 text-sm text-foreground-muted">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Блок 3: Последний заказ */}
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-foreground">Ваш последний заказ</h2>
          {!lastOrder ? (
            <Card className="rounded-2xl border border-dashed border-border p-8 text-center">
              <p className="text-sm text-foreground-muted">У вас пока нет заказов</p>
              <Button asChild className="mt-4">
                <Link href="/catalog">Перейти в каталог</Link>
              </Button>
            </Card>
          ) : (
            <Card className="rounded-2xl border border-border p-5 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-mono text-lg font-semibold text-foreground">
                      {lastOrder.order_number}
                    </p>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      className="h-9 px-3"
                      aria-label={`Скопировать номер заказа ${lastOrder.order_number}`}
                      onClick={() => void copyOrderNumber(lastOrder.order_number)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                  {orderCopyFeedback ? (
                    <p className="mt-1 text-xs text-brand" role="status">
                      {orderCopyFeedback}
                    </p>
                  ) : null}
                  <p className="mt-1 text-sm text-foreground-muted">
                    {new Date(lastOrder.created_at).toLocaleString('ru-RU')}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    Сумма: {money(lastOrder.total_amount)} {CURRENCY_SYMBOL}
                  </p>
                </div>
                <span
                  className={cn(
                    'inline-flex w-fit rounded-full px-3 py-1 text-xs font-semibold',
                    statusBadgeClass(lastOrder.status)
                  )}
                >
                  {STATUS_LABELS[lastOrder.status] ?? lastOrder.status}
                </span>
              </div>
              {lastOrder.items?.length > 0 && (
                <ul className="mt-4 flex flex-col gap-2 border-t border-border pt-4 sm:flex-row sm:flex-wrap">
                  {lastOrder.items.slice(0, 4).map(it => (
                    <li
                      key={it.id}
                      className="flex min-w-0 flex-1 items-center gap-3 rounded-xl bg-zinc-50 px-3 py-2 sm:min-w-[200px]"
                    >
                      <div className="grid h-12 w-12 shrink-0 place-items-center rounded-lg bg-white text-xs font-bold text-foreground-muted ring-1 ring-black/5">
                        {it.product_title.slice(0, 1)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-foreground">{it.product_title}</p>
                        <p className="text-xs text-foreground-muted">
                          {it.quantity} × {money(it.price)} {CURRENCY_SYMBOL}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-4">
                <Button asChild variant="outline">
                  <Link href={`/orders/${lastOrder.id}`}>Подробнее</Link>
                </Button>
              </div>
            </Card>
          )}
        </section>

        {/* Блок 4: Рейтинг менеджеров */}
        <Card className="mt-8 rounded-2xl border border-border p-5 shadow-sm">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-foreground">
            <Star className="h-5 w-5 text-amber-500" />
            Оцените работу менеджеров
          </h2>
          {ratingsSummary && (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-4xl font-semibold text-foreground">{ratingsSummary.average.toFixed(1)}</p>
                <p className="mt-1 text-sm text-foreground-muted">
                  из 5 · {ratingsSummary.count}{' '}
                  {ratingsSummary.count === 1 ? 'оценка' : ratingsSummary.count < 5 ? 'оценки' : 'оценок'}
                </p>
              </div>
              <Link href="/about#managers" className="text-sm font-medium text-primary hover:underline">
                Подробнее на странице «О нас»
              </Link>
            </div>
          )}
          {ordersToRate.length > 0 && (
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-sm text-foreground-muted">Заказы без оценки:</p>
              <ul className="space-y-2">
                {ordersToRate.map(order => (
                  <li
                    key={order.id}
                    className="flex flex-col gap-2 rounded-xl bg-zinc-50 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="text-sm text-foreground">
                      <span className="font-medium">Заказ {order.order_number}</span>
                      <span className="text-foreground-muted">
                        {' '}
                        · {formatRuDateShort(order.created_at)}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/order-rate?order_id=${order.id}`}>Оценить заказ</Link>
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        {/* Блок 5: Избранное */}
        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
              <Heart className="h-5 w-5 text-red-500" />
              Избранное
            </h2>
            <Link href="/wishlist" className="text-sm font-medium text-primary hover:underline">
              Всё избранное
            </Link>
          </div>
          {wishlistLoading ? (
            <Loading />
          ) : wishlistPreview.length === 0 ? (
            <Card className="rounded-2xl border border-dashed border-border p-6 text-center">
              <p className="text-sm text-foreground-muted">
                Добавляйте товары в избранное, чтобы не потерять
              </p>
              <Button asChild className="mt-4">
                <Link href="/catalog">Перейти в каталог</Link>
              </Button>
            </Card>
          ) : (
            <div className="no-scrollbar flex gap-3 overflow-x-auto pb-2">
              {wishlistPreview.map(w => {
                const img = productThumb(w.product);
                const imgUrl = img ? mediaUrl(img) : null;
                return (
                  <Card
                    key={w.id}
                    className="w-[220px] shrink-0 rounded-2xl border border-border p-3 shadow-sm"
                  >
                    <Link href={`/products/${w.product.slug}`} className="block">
                      <div className="relative mx-auto h-24 w-24 overflow-hidden rounded-xl bg-zinc-100">
                        {imgUrl ? (
                          <Image src={imgUrl} alt="" fill className="object-cover" sizes="96px" unoptimized />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-xs text-foreground-muted">
                            фото
                          </div>
                        )}
                      </div>
                      <p className="mt-2 line-clamp-2 text-sm font-medium text-foreground">{w.product.title}</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">
                        {money(w.product.price)} {CURRENCY_SYMBOL}
                      </p>
                    </Link>
                    <Button
                      type="button"
                      size="sm"
                      className="mt-3 w-full"
                      loading={addToCartMutation.isPending}
                      onClick={() => addToCartMutation.mutate(w.product.id)}
                    >
                      В корзину
                    </Button>
                  </Card>
                );
              })}
            </div>
          )}
          {wishlistMsg && <p className="mt-2 text-sm text-foreground-muted">{wishlistMsg}</p>}
        </section>

        {/* Блок 6: Адреса */}
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold text-foreground">Адреса доставки</h2>
          {addressesLoading ? (
            <Loading />
          ) : !defaultAddress ? (
            <Card className="rounded-2xl border border-dashed border-border p-6">
              <p className="text-sm text-foreground-muted">
                Добавьте адрес для быстрого оформления заказа
              </p>
              <Button asChild className="mt-4">
                <Link href="/profile/addresses">Добавить адрес</Link>
              </Button>
            </Card>
          ) : (
            <Card className="rounded-2xl border border-border p-5 shadow-sm">
              <div className="flex items-start gap-3">
                <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-foreground-muted" />
                <div className="min-w-0">
                  <p className="font-medium text-foreground">{defaultAddress.title}</p>
                  <p className="mt-1 text-sm text-foreground-muted">
                    {defaultAddress.city}, {defaultAddress.street}, д. {defaultAddress.house}
                    {defaultAddress.apartment ? `, кв. ${defaultAddress.apartment}` : ''}
                  </p>
                  {defaultAddress.is_default && (
                    <span className="mt-2 inline-block rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                      По умолчанию
                    </span>
                  )}
                </div>
              </div>
              <Button asChild variant="outline" className="mt-4">
                <Link href="/profile/addresses">Все адреса</Link>
              </Button>
            </Card>
          )}
        </section>

        {/* Блок 7: Уведомления */}
        <Card id="notifications" className="mt-8 rounded-2xl border border-border p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-foreground">Уведомления о статусе заказа</h2>
          <p className="mb-4 text-sm text-foreground-muted">
            Мы будем присылать обновления в рамках выбранных каналов. SMS и Telegram подключим отдельно.
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="flex cursor-pointer items-start gap-2 rounded-xl border border-border bg-white p-3">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 shrink-0 rounded border-border"
                checked={Boolean(user.marketing_opt_in)}
                disabled={marketingMutation.isPending}
                onChange={e => marketingMutation.mutate(e.target.checked)}
              />
              <span className="text-sm text-foreground">
                <span className="font-medium">Email / рассылка</span>
                <span className="mt-0.5 block text-xs text-foreground-muted">
                  Акции и полезные материалы (согласие можно отозвать)
                </span>
              </span>
            </label>
            <div className="rounded-xl border border-border bg-zinc-50 p-3 opacity-70">
              <p className="text-sm font-medium text-foreground">SMS</p>
              <p className="mt-1 text-xs text-foreground-muted">Скоро</p>
            </div>
            <div className="rounded-xl border border-border bg-zinc-50 p-3 opacity-70">
              <p className="text-sm font-medium text-foreground">Telegram</p>
              <p className="mt-1 text-xs text-foreground-muted">Скоро</p>
            </div>
          </div>
        </Card>

        {/* Персональные данные */}
        <Card id="privacy" className="mt-8 rounded-2xl border border-border p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-foreground">Персональные данные и согласия</h2>
          <p className="mb-4 text-sm text-foreground-muted">
            Согласие с политикой зафиксировано при регистрации
            {user.privacy_policy_accepted_at
              ? ` (${new Date(user.privacy_policy_accepted_at).toLocaleString('ru-RU')})`
              : ''}
            . Документы:{' '}
            <Link href="/docs/privacy" className="text-primary underline">
              Политика
            </Link>
            ,{' '}
            <Link href="/docs/offer" className="text-primary underline">
              Оферта
            </Link>
            .
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="inline-flex items-center gap-2"
              loading={exportMutation.isPending}
              onClick={() => exportMutation.mutate()}
            >
              <Download className="h-4 w-4" />
              Скачать копию моих данных (JSON)
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="inline-flex items-center gap-2 border-red-200 text-red-700 hover:bg-red-50"
              loading={deleteMutation.isPending}
              onClick={async () => {
                if (
                  !window.confirm(
                    'Удалить аккаунт? Профиль и адреса будут очищены, вход станет невозможен. Заказы в системе могут сохраняться для учёта. Продолжить?'
                  )
                ) {
                  return;
                }
                setPrivacyError('');
                try {
                  await deleteMutation.mutateAsync();
                  await logout();
                  router.push('/');
                } catch {
                  setPrivacyError(
                    'Не удалось удалить аккаунт. Попробуйте позже или напишите в поддержку.'
                  );
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
              Удалить аккаунт
            </Button>
          </div>
          {privacyError && <p className="mt-3 text-sm text-red-600">{privacyError}</p>}
        </Card>

        {/* Выход */}
        <div className="mt-8 flex justify-center sm:justify-start">
          <Button
            type="button"
            variant="outline"
            onClick={() => setLogoutOpen(true)}
            className="inline-flex items-center gap-2 border-red-200 text-red-700 hover:bg-red-50"
            aria-label="Выйти из аккаунта"
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </Button>
        </div>
      </div>

      <Modal isOpen={logoutOpen} onClose={() => setLogoutOpen(false)} title="Выход из аккаунта">
        <p className="mb-4 text-sm text-foreground-muted">Вы уверены, что хотите выйти?</p>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button type="button" variant="ghost" onClick={() => setLogoutOpen(false)}>
            Отмена
          </Button>
          <Button
            type="button"
            className="border-red-200 text-red-700 hover:bg-red-50"
            variant="outline"
            onClick={async () => {
              setLogoutOpen(false);
              await logout();
              router.push('/');
            }}
          >
            Да, выйти
          </Button>
        </div>
      </Modal>
    </div>
  );
}
