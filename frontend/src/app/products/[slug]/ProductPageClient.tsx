'use client';

import type { ReactElement } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ShoppingCart, Star, Zap } from 'lucide-react';
import type { ProductDetail, Store } from '@/types';
import { getStores } from '@/lib/api/services/stores.service';
import { addToCart } from '@/lib/api/services/cart.service';
import { stripDescriptionHtml } from '@/lib/format-description';
import { Loading } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import { ProductSpecsTable } from '@/components/features/products/ProductSpecsTable';
import { ProductTabs } from '@/components/features/products/ProductTabs';
import { Modal } from '@/components/ui/Modal';
import { ProductDetailRecommendations } from '@/components/features/products/ProductDetailRecommendations';
import { FreeDeliveryBadge } from '@/components/ui/FreeDeliveryBadge';
import { useProduct } from '@/lib/hooks/useProducts';
import { CURRENCY_SYMBOL } from '@/lib/constants';
import { getSpecValue, getSpecValues } from '@/lib/utils/product-specs';
import { Ringik, useRingikIntersectionTrigger } from '@/components/ringik/Ringik';
import { recordRecentlyViewedProduct } from '@/lib/recently-viewed-products';
import { useUiMode } from '@/lib/providers/UiModeProvider';
import { addToCartButtonLabel } from '@/lib/ui-mode/copy';
import { resolveProductDisplayPrice } from '@/lib/product-pricing';
import { mergeColorGroups } from '@/lib/product-colors';
import { ProductColorPicker } from '@/components/features/products/ProductColorPicker';
import { PageContainer } from '@/components/layout/PageContainer';

const ProductMediaArea = dynamic(
  () =>
    import('@/components/features/products/ProductMediaArea').then(m => ({
      default: m.ProductMediaArea,
    })),
  {
    loading: () => <div className="aspect-square w-full animate-pulse rounded-lg bg-zinc-200" />,
    ssr: false,
  }
);

const StoresMap = dynamic(
  () =>
    import('@/components/features/stores/StoresMap').then(m => ({
      default: m.StoresMap,
    })),
  {
    loading: () => <div className="h-64 w-full animate-pulse rounded-lg bg-zinc-200" />,
    ssr: false,
  }
);

interface ProductPageClientProps {
  slug: string;
  initialProduct: ProductDetail;
}

function ProductContent({ product }: { product: ProductDetail }): ReactElement {
  const { mode } = useUiMode();
  const [isOneClickOpen, setIsOneClickOpen] = useState(false);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [selectedColorId, setSelectedColorId] = useState<string | null>(null);
  const colorGroups = useMemo(
    () => mergeColorGroups(product.colors ?? []),
    [product.colors]
  );
  const [selectedGroupKey, setSelectedGroupKey] = useState<string | null>(null);

  useEffect(() => {
    if (!colorGroups.length) {
      setSelectedGroupKey(null);
      return;
    }
    const imgs = product.images ?? [];
    const withImg = colorGroups.find(g =>
      g.colorIds.some(id => imgs.some(img => img.color?.id === id))
    );
    setSelectedGroupKey((withImg ?? colorGroups[0]).key);
  }, [product.id, colorGroups, product.images]);

  useEffect(() => {
    const group = colorGroups.find(g => g.key === selectedGroupKey);
    setSelectedColorId(group?.colorIds[0] ?? null);
  }, [selectedGroupKey, colorGroups]);

  const displayPrice = useMemo(
    () => resolveProductDisplayPrice(product, selectedColorId),
    [product, selectedColorId]
  );
  const priceRef = useRef<HTMLDivElement>(null);
  const ringik = useRingikIntersectionTrigger(priceRef, `pdp_price_${product.slug ?? product.id}_v2`, {
    bubbleMs: 2000,
    visibleMs: 2600,
    threshold: 0.2,
    rootMargin: '0px 0px -25% 0px',
  });

  const isOutOfStock = product.availability_status === 'out_of_stock';

  const queryClient = useQueryClient();
  const addToCartMutation = useMutation({
    mutationFn: (quantity: number) =>
      addToCart(product.id, quantity, selectedStoreId ?? undefined, selectedColorId ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });

  const { data: storesData } = useQuery({
    queryKey: ['stores', 'active'],
    queryFn: () => getStores({ is_active: true }),
  });

  const stores: Store[] = storesData?.results ?? [];

  const stockList = product.stock ?? [];
  const productStores = stockList
    .map(stock => {
      const store = stores.find(s => s.id === stock.store);
      if (!store) return null;
      return { store, quantity: stock.available_quantity };
    })
    .filter((item): item is { store: Store; quantity: number } => Boolean(item));

  return (
    <>
    <PageContainer wide className="pb-24 py-6 lg:pb-6">
      <div className="flex flex-col gap-6 lg:grid lg:grid-cols-[1fr_1fr] lg:gap-10">
        <div className="min-w-0 w-full overflow-hidden">
          <ProductMediaArea
            product={product}
            selectedGroupKey={selectedGroupKey}
            onActiveColorIdChange={setSelectedColorId}
          />
        </div>

        <div className="w-full rounded-[32px] border border-border bg-white p-4 sm:p-7 lg:w-auto lg:p-10">
          <div className="mb-3 flex items-center gap-1 text-sm text-zinc-800">
            <Star className="h-4 w-4 fill-zinc-900 text-zinc-900" />
            <Star className="h-4 w-4 fill-zinc-900 text-zinc-900" />
            <Star className="h-4 w-4 fill-zinc-900 text-zinc-900" />
            <Star className="h-4 w-4 fill-zinc-900 text-zinc-900" />
            <Star className="h-4 w-4 fill-zinc-900 text-zinc-900" />
            <span className="ml-1 text-xs text-foreground-muted">
              {product.reviews_count} отзывов
            </span>
          </div>

          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl font-semibold leading-tight tracking-tight text-foreground sm:text-3xl lg:max-w-[28rem] lg:text-5xl">
                {product.title ?? 'Без названия'}
              </h1>
              <p className="mt-2 text-sm text-foreground-muted">
                {stripDescriptionHtml(product.short_description) ||
                  stripDescriptionHtml(product.description).slice(0, 200) ||
                  'Премиальные материалы и точная посадка под устройство.'}
              </p>
            </div>
            <div ref={priceRef} className="relative shrink-0 text-left sm:text-right">
              <p
                className="text-3xl font-semibold leading-none text-foreground sm:text-[44px] lg:text-[56px]"
                data-seo-price={displayPrice.price ?? ''}
              >
                {displayPrice.price ? Math.round(Number(displayPrice.price)) : '—'}
              </p>
              {displayPrice.old_price && (
                <p className="text-base text-foreground-muted line-through">
                  {Math.round(Number(displayPrice.old_price))} {CURRENCY_SYMBOL}
                </p>
              )}
              <p className="text-sm text-foreground-muted">{CURRENCY_SYMBOL}</p>

              <Ringik
                pose="sitting"
                placement="absolute"
                visible={ringik.visible}
                showMessage={ringik.showMessage}
                message="Топ за свои деньги!"
                className="pointer-events-none hidden scale-[1.05] lg:pointer-events-auto lg:absolute lg:-right-6 lg:-top-12 lg:block"
              />
            </div>
          </div>

          <div className="mb-4 rounded-2xl border border-border bg-[#f7f7f7] p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 shrink-0">
                <p className="text-xs uppercase tracking-wide text-foreground-muted">Устройство</p>
                <p className="mt-2 inline-flex rounded-full border border-zinc-900 px-3 py-1 text-sm font-medium text-zinc-900">
                  {product.category?.title ?? '—'}
                </p>
              </div>
              <ProductColorPicker
                product={product}
                selectedGroupKey={selectedGroupKey}
                onSelectGroupKey={setSelectedGroupKey}
              />
            </div>
          </div>

          <FreeDeliveryBadge className="mb-4" size="sm" />

          {(() => {
            const materials = getSpecValues(product, 'Материал');
            if (materials.length === 0) return null;
            return (
              <div className="mb-4">
                <p className="mb-2 text-sm font-medium text-foreground">Материал</p>
                <div className="grid gap-2 sm:grid-cols-3">
                  {materials.map((material, i) => (
                    <span
                      key={`${material}-${i}`}
                      className={`rounded-2xl border p-3 text-left text-sm ${
                        i === 0
                          ? 'border-zinc-900 bg-white'
                          : 'border-border bg-[#f7f7f7] text-foreground-muted'
                      }`}
                    >
                      {material}
                    </span>
                  ))}
                </div>
              </div>
            );
          })()}

          <p className="mb-3 text-xs text-foreground-muted" data-seo-availability={isOutOfStock ? 'out' : 'in'}>
            {isOutOfStock ? 'Нет в наличии' : 'В наличии'}
            {product.sku ? ` • Артикул: ${product.sku}` : ''}
            {product.brand ? ` • Бренд: ${product.brand}` : ''}
          </p>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              fullWidth
              loading={addToCartMutation.isPending}
              onClick={() => addToCartMutation.mutate(1)}
              disabled={isOutOfStock}
            >
              <ShoppingCart className="mr-2 h-4 w-4" />
              {addToCartButtonLabel(mode, isOutOfStock)}
            </Button>
            <Button variant="secondary" fullWidth onClick={() => setIsOneClickOpen(true)}>
              <Zap className="mr-2 h-4 w-4" />
              Купить в 1 клик
            </Button>
          </div>

          <Link href="/catalog" className="mt-4 inline-flex text-sm text-info hover:underline">
            ← Назад в каталог
          </Link>
        </div>
      </div>

      <ProductSpecsTable product={product} />
      <ProductTabs product={product} />

      {productStores.length > 0 && (
        <section className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div>
            <h2 className="mb-3 text-lg font-semibold text-foreground">Наличие в магазинах</h2>
            <div className="overflow-hidden rounded-xl border border-border bg-white ">
              <ul className="divide-y divide-border text-sm">
                {productStores.map(({ store, quantity }) => (
                  <li
                    key={store.id}
                    className={`cursor-pointer px-4 py-3 transition-colors ${
                      selectedStoreId === store.id
                        ? 'bg-zinc-100 '
                        : 'hover:bg-zinc-50 hover:bg-zinc-50'
                    }`}
                    onClick={() => setSelectedStoreId(store.id)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="font-medium text-foreground">{store.name}</p>
                        <p className="text-xs text-foreground-muted">
                          {store.city}, {store.address}
                        </p>
                      </div>
                      <span className="text-xs text-foreground-muted">Доступно: {quantity}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div>
            <h2 className="mb-3 text-lg font-semibold text-foreground">Магазины на карте</h2>
            <StoresMap
              stores={productStores.map(item => item.store)}
              selectedStoreId={selectedStoreId}
              onSelectStore={setSelectedStoreId}
            />
          </div>
        </section>
      )}

      <section className="mt-10 grid gap-4">
        <div className="rounded-2xl border border-border bg-card p-5">
          <h3 className="mb-2 text-lg font-semibold text-foreground">Рассрочка</h3>
          <p className="mb-4 text-sm text-foreground-muted">
            Оформите покупку в рассрочку без переплат. Условия и сроки уточняйте у партнёрского
            банка при оформлении заказа.
          </p>
          <Link
            href="/installment"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            Подробнее об условиях рассрочки
          </Link>
        </div>
        <ProductDetailRecommendations product={product} />
      </section>

      <Modal
        isOpen={isOneClickOpen}
        onClose={() => setIsOneClickOpen(false)}
        title="Купить в 1 клик"
      >
        <p className="mb-4 text-sm text-foreground-muted">
          Здесь будет форма для быстрого заказа. Пока это заглушка.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setIsOneClickOpen(false)}>
            Отмена
          </Button>
          <Button onClick={() => setIsOneClickOpen(false)}>Отправить заявку</Button>
        </div>
      </Modal>
    </PageContainer>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-white/95 backdrop-blur lg:hidden">
        <div className="mx-auto flex w-full max-w-7xl gap-2 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <Button
            fullWidth
            loading={addToCartMutation.isPending}
            onClick={() => addToCartMutation.mutate(1)}
            disabled={isOutOfStock}
          >
            <ShoppingCart className="mr-2 h-4 w-4" />
            {addToCartButtonLabel(mode, isOutOfStock)}
          </Button>
        </div>
      </div>
    </>
  );
}

export function ProductPageClient({ slug, initialProduct }: ProductPageClientProps): ReactElement {
  const { data: product, isLoading, isError } = useProduct(slug, {
    initialData: initialProduct,
  });

  useEffect(() => {
    if (product) recordRecentlyViewedProduct(product);
  }, [product]);

  if (isLoading && !product) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
        <h1 className="mb-2 text-xl font-semibold text-foreground">Товар не найден</h1>
        <p className="mb-4 text-sm text-foreground-muted">
          Возможно, этот товар был удалён или временно недоступен.
        </p>
        <Link href="/catalog" className="text-sm text-info hover:underline">
          Вернуться в каталог
        </Link>
      </div>
    );
  }

  return <ProductContent product={product} />;
}
