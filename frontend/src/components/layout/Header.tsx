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
import {
  HEADER_ACTIONS_CLUSTER_CLASS,
  HEADER_BADGE_CLASS,
  HEADER_BRAND_CLUSTER_CLASS,
  HEADER_CATALOG_BUTTON_CLASS,
  HEADER_FIXED_CLASS,
  HEADER_ICON_BUTTON_CLASS,
  HEADER_ICONS_ROW_CLASS,
  HEADER_LOGO_BOX_CLASS,
  HEADER_NAV_CLASS,
  HEADER_OUTER_CLASS,
  HEADER_PILL_CLASS,
  HEADER_PILL_INNER_CLASS,
} from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';
import { BrandLogo } from '@/components/layout/BrandLogo';
import { LINK_PREFETCH_DEFAULT } from '@/lib/navigation/link-prefetch';

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
    <header className={HEADER_FIXED_CLASS}>
      <div className={HEADER_OUTER_CLASS}>
        <div
          className={cn(
            HEADER_PILL_CLASS,
            HEADER_PILL_INNER_CLASS,
            'max-md:pl-[max(0.5rem,env(safe-area-inset-left))] max-md:pr-[max(0.25rem,env(safe-area-inset-right))]'
          )}
        >
          <div className={HEADER_BRAND_CLUSTER_CLASS}>
            <BrandLogo
              href="/"
              onClick={onLogoClick}
              boxClassName={HEADER_LOGO_BOX_CLASS}
              priority
            />
            <Link
              href="/catalog"
              prefetch={LINK_PREFETCH_DEFAULT}
              aria-label="Каталог"
              className={cn(
                HEADER_CATALOG_BUTTON_CLASS,
                catalogActive && 'ring-2 ring-[var(--color-brand)] ring-offset-2 ring-offset-white'
              )}
              aria-current={catalogActive ? 'page' : undefined}
            >
              <LayoutGrid className="shrink-0" aria-hidden />
              <span className="whitespace-nowrap">Каталог</span>
            </Link>
          </div>

          <nav className={HEADER_NAV_CLASS} aria-label="Основная навигация">
            {navItems
              .filter(item => item.href !== '/catalog')
              .map(item => {
                const active = isNavActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    prefetch={LINK_PREFETCH_DEFAULT}
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

          <div className={cn(HEADER_ACTIONS_CLUSTER_CLASS, 'max-md:col-span-1 md:col-start-3')}>
            <HeaderSearch ref={headerSearchRef} />
            <UiModeToggle variant="header" />
            <div className={HEADER_ICONS_ROW_CLASS}>
              <Link
                href="/wishlist"
                prefetch={LINK_PREFETCH_DEFAULT}
                className={HEADER_ICON_BUTTON_CLASS}
                aria-label={
                  wishlistCount > 0 ? `Избранное, ${wishlistCount} товаров` : 'Избранное'
                }
              >
                <Heart className="text-foreground" />
                {wishlistCount > 0 && (
                  <span className={HEADER_BADGE_CLASS}>
                    {wishlistCount > 99 ? '99+' : wishlistCount}
                  </span>
                )}
              </Link>
              <button
                ref={cartFly?.registerCartRef}
                type="button"
                onClick={onCartClick}
                className={HEADER_ICON_BUTTON_CLASS}
                aria-label={cartCount > 0 ? `Корзина, ${cartCount} товаров` : 'Корзина'}
              >
                <ShoppingBag className="text-foreground" />
                {cartCount > 0 && (
                  <span className={HEADER_BADGE_CLASS}>
                    {cartCount > 99 ? '99+' : cartCount}
                  </span>
                )}
              </button>
              <button
                type="button"
                className={cn(HEADER_ICON_BUTTON_CLASS, 'md:hidden')}
                onClick={() => setMobileOpen(true)}
                aria-label="Меню"
              >
                <Menu className="text-foreground" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <MobileMenu
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        navItems={navItems}
      />
    </header>
  );
}
