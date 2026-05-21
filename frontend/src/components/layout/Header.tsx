'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShoppingBag, Menu, LayoutGrid, Heart } from 'lucide-react';
import { MobileMenu } from '@/components/layout/MobileMenu';
import { UiModeToggle } from '@/components/ui-mode/UiModeToggle';
import { HeaderSearch, type HeaderSearchHandle } from '@/components/layout/HeaderSearch';
import { useCartFly } from '@/lib/providers/CartFlyProvider';
import { isNavActive } from '@/lib/navigation/is-nav-active';
import { HEADER_ICON_BUTTON_CLASS, HEADER_OUTER_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';
import { BrandLogo } from '@/components/layout/BrandLogo';

interface HeaderProps {
  cartCount?: number;
  wishlistCount?: number;
  onCartClick?: () => void;
  onLogoClick?: () => void;
}

const navItems = [
  { href: '/catalog', label: 'Каталог' },
  { href: '/promotions', label: 'Акции' },
  { href: '/stores', label: 'Магазины' },
  { href: '/about', label: 'О нас' },
  { href: '/order-status', label: 'Проверить заказ' },
  { href: '/profile', label: 'Профиль' },
];

const headerPillClass =
  'rounded-full border-2 border-[var(--color-brand)] bg-white shadow-[0_0_0_1px_rgba(34,197,94,0.35),0_0_18px_rgba(34,197,94,0.28),0_0_42px_rgba(34,197,94,0.14)]';

export function Header({
  cartCount = 0,
  wishlistCount = 0,
  onCartClick,
  onLogoClick,
}: HeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const headerSearchRef = useRef<HeaderSearchHandle>(null);
  const cartFly = useCartFly();
  const pathname = usePathname();
  const catalogActive = isNavActive(pathname, '/catalog');

  return (
    <header className="sticky top-0 z-40 bg-transparent pt-[env(safe-area-inset-top,0px)]">
      <div className={HEADER_OUTER_CLASS}>
        <div
          className={cn(
            'flex flex-nowrap items-center gap-1.5 px-2 py-2 sm:gap-2 sm:px-4 sm:py-2.5 md:px-6 md:py-3.5 lg:gap-4',
            headerPillClass
          )}
        >
          <div className="flex min-w-0 shrink-0 items-center gap-1 sm:gap-1.5 md:pr-2">
            <BrandLogo href="/" onClick={onLogoClick} height={56} width={112} className="md:hidden" />
            <BrandLogo
              href="/"
              onClick={onLogoClick}
              height={76}
              width={132}
              className="hidden md:inline-flex"
            />
            <Link
              href="/catalog"
              className={cn(
                'inline-flex min-h-[44px] shrink-0 items-center gap-1 rounded-full px-2.5 py-2 text-xs font-semibold text-white transition-all duration-200 touch-manipulation sm:min-h-0 sm:gap-1.5 sm:px-4 sm:py-2.5 sm:text-sm md:text-base',
                'bg-[var(--color-brand)] hover:brightness-110',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand)] focus-visible:ring-offset-2',
                catalogActive && 'ring-2 ring-[var(--color-brand)] ring-offset-2 ring-offset-white'
              )}
              aria-current={catalogActive ? 'page' : undefined}
            >
              <LayoutGrid className="h-4 w-4 shrink-0" />
              <span className="whitespace-nowrap">Каталог</span>
            </Link>
          </div>

          <nav
            className="hidden min-w-0 flex-1 flex-nowrap items-center justify-center gap-x-2 text-sm font-semibold text-foreground md:flex lg:gap-x-6 lg:text-base xl:gap-x-7"
            aria-label="Основная навигация"
          >
            {navItems
              .filter(item => item.href !== '/catalog')
              .map(item => {
                const active = isNavActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    scroll
                    className={cn(
                      'whitespace-nowrap transition-colors duration-200',
                      'focus-visible:rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand)] focus-visible:ring-offset-2',
                      active
                        ? 'text-[var(--color-brand)]'
                        : 'text-foreground hover:text-[var(--color-brand)]'
                    )}
                    aria-current={active ? 'page' : undefined}
                  >
                    {item.label}
                  </Link>
                );
              })}
          </nav>

          <div className="flex min-w-0 shrink-0 items-center justify-end gap-0.5 sm:gap-2 md:ml-auto lg:gap-3">
            <HeaderSearch ref={headerSearchRef} />
            <UiModeToggle variant="header-compact" />
            <UiModeToggle variant="header" />
            <div className="flex shrink-0 items-center gap-0.5 sm:gap-1">
              <Link
                href="/wishlist"
                className={HEADER_ICON_BUTTON_CLASS}
                aria-label={
                  wishlistCount > 0 ? `Избранное, ${wishlistCount} товаров` : 'Избранное'
                }
              >
                <span className="relative inline-flex">
                  <Heart className="h-5 w-5 text-foreground sm:h-6 sm:w-6" />
                  {wishlistCount > 0 && (
                    <span className="absolute -right-2 -top-2 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-brand)] px-1 text-[10px] font-semibold text-white">
                      {wishlistCount > 99 ? '99+' : wishlistCount}
                    </span>
                  )}
                </span>
              </Link>
              <button
                ref={cartFly?.registerCartRef}
                type="button"
                onClick={onCartClick}
                className={HEADER_ICON_BUTTON_CLASS}
                aria-label={cartCount > 0 ? `Корзина, ${cartCount} товаров` : 'Корзина'}
              >
                <span className="relative inline-flex">
                  <ShoppingBag className="h-5 w-5 text-foreground sm:h-6 sm:w-6" />
                  {cartCount > 0 && (
                    <span className="absolute -right-2 -top-2 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-brand)] px-1 text-[10px] font-semibold text-white">
                      {cartCount > 99 ? '99+' : cartCount}
                    </span>
                  )}
                </span>
              </button>

              <button
                type="button"
                className={cn(HEADER_ICON_BUTTON_CLASS, 'md:hidden')}
                onClick={() => setMobileOpen(true)}
                aria-label="Меню"
              >
                <Menu className="h-5 w-5 text-foreground" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <MobileMenu
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        cartCount={cartCount}
        wishlistCount={wishlistCount}
        navItems={navItems}
        onCartClick={onCartClick}
        onRequestMobileSearch={() => {
          queueMicrotask(() => headerSearchRef.current?.openMobilePanel());
        }}
      />
    </header>
  );
}
