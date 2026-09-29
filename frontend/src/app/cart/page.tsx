'use client';

import { useMemo, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ShoppingCart } from 'lucide-react';
import Link from 'next/link';
import { useCart, useRemoveCartItem, useUpdateCartItem } from '@/lib/hooks/useCart';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { Skeleton } from '@/components/ui/Loading';
import { PlaceholderBlock } from '@/components/ui/PlaceholderBlock';
import { FreeDeliveryHighlight } from '@/components/ui/FreeDeliveryBadge';
import { CartItem } from '@/components/features/cart/CartItem';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getFriendlyErrorMessage } from '@/lib/errors';
import { Ringik } from '@/components/ringik/Ringik';
import { PageContainer } from '@/components/layout/PageContainer';

export default function CartPage() {
  const { data: cart, isLoading, isError, error } = useCart();
  const updateMutation = useUpdateCartItem();
  const removeMutation = useRemoveCartItem();
  const [promoCode, setPromoCode] = useState('');

  const totalAmount = cart?.total_amount ?? '0.00';

  const isEmpty = !cart || cart.items.length === 0;

  const items = useMemo(() => cart?.items ?? [], [cart]);

  if (isLoading) {
    return (
      <PageContainer className="py-6">
        <Skeleton className="mb-6 h-8 w-48" />
        <div className="flex flex-col gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex gap-4 rounded-xl border border-border bg-white p-4">
              <Skeleton className="h-24 w-24 shrink-0 rounded-lg" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-9 w-28" />
              </div>
            </div>
          ))}
        </div>
      </PageContainer>
    );
  }

  if (isError) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
        <p className="mb-2 text-sm text-danger">{getFriendlyErrorMessage(error)}</p>
        <p className="mb-4 text-xs text-foreground-muted">Не удалось загрузить корзину.</p>
        <Button asChild>
          <Link href="/catalog">В каталог</Link>
        </Button>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="relative flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
        <Ringik
          pose="sad"
          placement="absolute"
          visible
          showMessage
          message="Пусто... Добавь меня!"
          className="top-10"
        />
        <div className="mb-4">
          <ShoppingCart className="mx-auto mb-2 h-10 w-10 text-foreground-subtle" />
        </div>
        <h1 className="mb-2 text-xl font-semibold text-foreground">Ваша корзина пуста</h1>
        <p className="mb-6 max-w-md text-sm text-foreground-muted">
          Найдите интересные товары в каталоге и добавьте их в корзину, чтобы оформить заказ.
        </p>
        <Button asChild>
          <Link href="/catalog">Перейти в каталог</Link>
        </Button>
      </div>
    );
  }

  return (
    <PageContainer className="py-6">
      <h1 className="mb-6 text-2xl font-semibold text-foreground">Корзина</h1>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex-1 space-y-4">
          <AnimatePresence initial={false}>
            {items.map(item => {
              const handleDecrease = () => {
                if (item.quantity > 1) {
                  updateMutation.mutate({ itemId: item.id, quantity: item.quantity - 1 });
                }
              };

              const handleIncrease = () => {
                updateMutation.mutate({ itemId: item.id, quantity: item.quantity + 1 });
              };

              return (
                <CartItem
                  key={item.id}
                  item={item}
                  onDecrease={handleDecrease}
                  onIncrease={handleIncrease}
                  onRemove={() => removeMutation.mutate(item.id)}
                />
              );
            })}
          </AnimatePresence>
        </div>

        <aside className="w-full space-y-4 lg:sticky lg:top-24 lg:w-80 lg:max-w-sm">
          <Card className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Итоги</h2>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-foreground-muted">Сумма товаров</span>
                <span className="font-medium text-foreground">
                  {totalAmount} {CURRENCY_SYMBOL}
                </span>
              </div>
              <div>
                <label className="mb-1 block text-sm text-zinc-600 dark:text-zinc-400">
                  Промокод
                </label>
                <div className="flex gap-2">
                  <Input
                    value={promoCode}
                    onChange={e => setPromoCode(e.target.value)}
                    placeholder="Введите промокод"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!promoCode}
                    className="whitespace-nowrap"
                  >
                    Применить
                  </Button>
                </div>
              </div>
            </div>
            <FreeDeliveryHighlight />
            <Button fullWidth asChild>
              <Link href="/checkout">Оформить заказ</Link>
            </Button>
          </Card>
        </aside>
      </div>

      <div className="mt-8 grid gap-4">
        <PlaceholderBlock
          title="Блок: Рекомендованные товары к покупке"
          note="Тут будет кросс-сейл на основе корзины."
        />
      </div>
    </PageContainer>
  );
}
