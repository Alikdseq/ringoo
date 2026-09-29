'use client';

import { usePathname, useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useMemo } from 'react';
import { usePrefersReducedMotion } from '@/lib/hooks/usePrefersReducedMotion';
import { useCart } from '@/lib/hooks/useCart';
import { useAuth } from '@/lib/hooks/useAuth';
import { useWishlist } from '@/lib/hooks/useWishlist';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { HEADER_MAIN_OFFSET_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';
import type { Category } from '@/types';

function shouldAnimateRoute(pathname: string | null): boolean {
  if (!pathname) return true;
  if (pathname.startsWith('/catalog')) return false;
  if (pathname.startsWith('/products/')) return false;
  return true;
}

export function AppShell({
  children,
  initialCategories,
}: {
  children: React.ReactNode;
  initialCategories?: Category[];
}) {
  const pathname = usePathname();
  const router = useRouter();
  const reducedMotion = usePrefersReducedMotion();
  const animateRoute = shouldAnimateRoute(pathname) && !reducedMotion;
  const pageTransition = useMemo(
    () =>
      reducedMotion
        ? { initial: false as const, animate: {}, exit: {}, transition: { duration: 0 } }
        : {
            initial: { y: 6 },
            animate: { y: 0 },
            exit: { opacity: 0, y: -4 },
            transition: { duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] as const },
          },
    [reducedMotion]
  );
  const { data: cart } = useCart();
  const cartCount = cart?.items?.length ?? 0;
  const { isAuthenticated } = useAuth();
  const { count: wishlistCount } = useWishlist({ enabled: isAuthenticated });

  useEffect(() => {
    // Next/AppShell анимации могут сохранять scroll.
    // Для страницы акций всегда стартуем сверху.
    if (pathname !== '/promotions') return;
    requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: 'auto' }));
  }, [pathname]);

  return (
    <div className="relative flex min-h-screen w-full min-w-0 max-w-full flex-col">
      <Header
        cartCount={cartCount}
        wishlistCount={wishlistCount ?? 0}
        onLogoClick={() => router.push('/')}
        onCartClick={() => router.push('/cart')}
      />
      <main
        className={cn(
          'relative min-w-0 w-full max-w-full flex-1 overflow-x-clip',
          HEADER_MAIN_OFFSET_CLASS
        )}
      >
        {animateRoute ? (
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={pageTransition.initial}
              animate={pageTransition.animate}
              exit={pageTransition.exit}
              transition={pageTransition.transition}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        ) : (
          <div key={pathname}>{children}</div>
        )}
      </main>
      <Footer initialCategories={initialCategories} />
    </div>
  );
}
