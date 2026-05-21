'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import {
  ChevronRight,
  Heart,
  Info,
  LayoutGrid,
  MapPin,
  PackageSearch,
  Percent,
  Search,
  ShoppingBag,
  User,
  X,
} from 'lucide-react';
import { cn } from '@/lib/theme/utils';
import { BrandLogo } from '@/components/layout/BrandLogo';
import { UiModeToggle } from '@/components/ui-mode/UiModeToggle';
import { isNavActive } from '@/lib/navigation/is-nav-active';

interface NavItem {
  href: string;
  label: string;
}

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  navItems: NavItem[];
  cartCount?: number;
  wishlistCount?: number;
  onCartClick?: () => void;
  /** Открыть полноэкранный поиск (после закрытия меню). */
  onRequestMobileSearch?: () => void;
}

const MOBILE_CARD_META: Record<
  string,
  { subtitle: string; icon: LucideIcon; badge?: string }
> = {
  '/catalog': { subtitle: 'Смартфоны, техника и аксессуары', icon: LayoutGrid },
  '/promotions': { subtitle: 'Скидки и спецпредложения', icon: Percent, badge: 'HOT' },
  '/stores': { subtitle: 'Адреса и часы работы', icon: MapPin },
  '/about': { subtitle: 'О компании Ringoo', icon: Info },
  '/order-status': { subtitle: 'Статус по номеру заказа', icon: PackageSearch },
  '/profile': { subtitle: 'Заказы и данные', icon: User },
};

export function MobileMenu({
  isOpen,
  onClose,
  navItems,
  cartCount = 0,
  wishlistCount = 0,
  onCartClick,
  onRequestMobileSearch,
}: MobileMenuProps) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  const handleCartClick = () => {
    onClose();
    onCartClick?.() ?? router.push('/cart');
  };

  const handleOpenSearch = () => {
    onClose();
    requestAnimationFrame(() => onRequestMobileSearch?.());
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Меню навигации"
        >
          <motion.button
            type="button"
            aria-label="Закрыть меню"
            className="absolute inset-0 bg-black/20 backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.div
            className="pointer-events-none absolute inset-x-0 top-0 z-10 flex max-h-[100dvh] flex-col px-2 pt-[max(0.5rem,env(safe-area-inset-top))]"
            initial={{ y: '-104%', opacity: 0.6 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '-104%', opacity: 0.5 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320, mass: 0.85 }}
          >
            <div
              className="pointer-events-auto flex max-h-[min(100dvh-0.5rem,640px)] flex-col overflow-hidden rounded-2xl border border-white/40 bg-transparent shadow-[0_8px_40px_rgba(0,0,0,0.12)]"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border/60 bg-white/95 px-3 py-2.5 backdrop-blur-md supports-[backdrop-filter]:bg-white/88">
                <BrandLogo href="/" onClick={onClose} height={64} />
                <div className="flex shrink-0 items-center gap-0.5">
                  <button
                    type="button"
                    onClick={handleOpenSearch}
                    className="inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-full text-foreground transition-colors hover:bg-zinc-100"
                    aria-label="Поиск"
                  >
                    <Search className="h-5 w-5" />
                  </button>
                  <Link
                    href="/wishlist"
                    onClick={onClose}
                    className="relative inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-full text-foreground transition-colors hover:bg-zinc-100"
                    aria-label="Избранное"
                  >
                    <Heart className="h-5 w-5" />
                    {wishlistCount > 0 && (
                      <span className="absolute right-1 top-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-brand)] px-1 text-[9px] font-bold text-white">
                        {wishlistCount > 99 ? '99+' : wishlistCount}
                      </span>
                    )}
                  </Link>
                  <button
                    type="button"
                    onClick={handleCartClick}
                    className="relative inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-full text-foreground transition-colors hover:bg-zinc-100"
                    aria-label="Корзина"
                  >
                    <ShoppingBag className="h-5 w-5" />
                    {cartCount > 0 && (
                      <span className="absolute right-1 top-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-brand)] px-1 text-[9px] font-bold text-white">
                        {cartCount > 99 ? '99+' : cartCount}
                      </span>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Закрыть меню"
                    className="inline-flex min-h-[44px] min-w-[44px] touch-manipulation items-center justify-center rounded-full bg-zinc-900 text-white transition-colors hover:bg-zinc-800"
                  >
                    <X className="h-5 w-5" strokeWidth={2} />
                  </button>
                </div>
              </div>

              <nav
                className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden bg-transparent px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
                aria-label="Мобильное меню"
              >
                <UiModeToggle variant="mobile" />
                <ul className="flex flex-col gap-1.5">
                  {navItems.map(item => {
                    const active = isNavActive(pathname, item.href);
                    const meta = MOBILE_CARD_META[item.href] ?? {
                      subtitle: 'Перейти в раздел',
                      icon: LayoutGrid,
                    };
                    const Icon = meta.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          scroll
                          onClick={onClose}
                          aria-current={active ? 'page' : undefined}
                          className={cn(
                            'flex min-h-[48px] items-center gap-2.5 rounded-xl border bg-white/95 px-2.5 py-2 shadow-sm backdrop-blur-sm transition-colors',
                            'border-border/90 active:bg-zinc-50',
                            active
                              ? 'border-[var(--color-brand)]/70 ring-1 ring-[var(--color-brand)]/25'
                              : 'hover:border-[var(--color-brand)]/35'
                          )}
                        >
                          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-[var(--color-brand)]">
                            <Icon className="h-[22px] w-[22px]" strokeWidth={2} />
                          </span>
                          <span className="min-w-0 flex-1 text-left">
                            <span className="flex flex-wrap items-center gap-1.5">
                              <span className="text-sm font-bold leading-tight text-foreground">
                                {item.label}
                              </span>
                              {meta.badge && (
                                <span className="rounded-full bg-[var(--color-brand)] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white">
                                  {meta.badge}
                                </span>
                              )}
                            </span>
                            <span className="mt-0.5 block text-[11px] leading-snug text-foreground-muted">
                              {meta.subtitle}
                            </span>
                          </span>
                          <ChevronRight
                            className="h-5 w-5 shrink-0 text-foreground-muted"
                            aria-hidden
                          />
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
