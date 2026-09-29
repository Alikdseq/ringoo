'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Heart, Trash2 } from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import { useWishlist } from '@/lib/hooks/useWishlist';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Loading } from '@/components/ui/Loading';
import { ProductCard } from '@/components/features/products/ProductCard';
import type { Product } from '@/types';
import { PageContainer } from '@/components/layout/PageContainer';
import { PRODUCT_CARD_GRID_CLASS } from '@/lib/theme/spacing';

export default function WishlistPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, hasToken } = useAuth();
  const { items, isLoading, removeMutation } = useWishlist({
    enabled: !authLoading && isAuthenticated,
  });

  useEffect(() => {
    if (authLoading) return;
    if (hasToken) return;
    if (!isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent('/wishlist')}`);
    }
  }, [authLoading, hasToken, isAuthenticated, router]);

  if (authLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loading />
      </div>
    );
  }

  return (
    <PageContainer className="py-8">
      <nav
        className="mb-6 flex items-center gap-2 text-sm text-foreground-muted"
        aria-label="Хлебные крошки"
      >
        <Link href="/" className="hover:text-foreground">
          Главная
        </Link>
        <span aria-hidden>/</span>
        <Link href="/profile" className="hover:text-foreground">
          Профиль
        </Link>
        <span aria-hidden>/</span>
        <span className="text-foreground">Избранное</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold text-foreground">Избранное</h1>

      {items.length === 0 ? (
        <Card className="flex flex-col items-center justify-center p-12 text-center">
          <Heart className="mb-4 h-12 w-12 text-foreground-muted opacity-50" />
          <p className="mb-6 text-foreground-muted">
            В избранном пока ничего нет. Добавляйте товары с карточки в каталоге.
          </p>
          <Button asChild>
            <Link href="/catalog">В каталог</Link>
          </Button>
        </Card>
      ) : (
        <div className={PRODUCT_CARD_GRID_CLASS}>
          {items.map(item => (
            <div key={item.id} className="relative">
              <ProductCard product={item.product as Product} />
              <button
                type="button"
                onClick={() => removeMutation.mutate(item.product.id)}
                disabled={removeMutation.isPending}
                className="absolute right-2 top-2 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-red-500 shadow hover:bg-white"
                aria-label="Удалить из избранного"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
