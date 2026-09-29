'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import Link from 'next/link';
import { LINK_PREFETCH_DEFAULT } from '@/lib/navigation/link-prefetch';
import { usePathname } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import {
  ChevronRight,
  Info,
  LayoutGrid,
  MapPin,
  PackageSearch,
  Percent,
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

export function MobileMenu({ isOpen, onClose, navItems }: MobileMenuProps) {
  const pathname = usePathname();
  const [portalReady, setPortalReady] = useState(false);

  useEffect(() => {
    setPortalReady(true);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  const menu = (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-[200] w-full max-w-[100vw] overflow-hidden md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Меню навигации"
        >
          <button
            type="button"
            aria-label="Закрыть меню"
            className="absolute inset-0 cursor-default bg-transparent"
            onClick={onClose}
          />
          <motion.div
            className="pointer-events-none absolute inset-x-0 top-0 z-10 flex w-full max-w-full max-h-[100dvh] flex-col px-2 pt-[max(0.5rem,env(safe-area-inset-top))]"
            initial={{ y: '-104%', opacity: 0.6 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: '-104%', opacity: 0.5 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320, mass: 0.85 }}
          >
            <div
              className="pointer-events-auto mx-auto flex w-full max-w-full max-h-[min(100dvh-0.5rem,640px)] flex-col overflow-hidden bg-transparent"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex min-w-0 shrink-0 items-center justify-between gap-2 border-b border-border/60 bg-white/95 px-3 py-2.5 backdrop-blur-md supports-[backdrop-filter]:bg-white/88">
                <BrandLogo
                  href="/"
                  onClick={onClose}
                  boxClassName="h-12 w-[min(120px,40vw)] max-w-[40vw] shrink-0"
                />
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Закрыть меню"
                  className="inline-flex min-h-[44px] min-w-[44px] shrink-0 touch-manipulation items-center justify-center rounded-full bg-zinc-900 text-white transition-colors hover:bg-zinc-800"
                >
                  <X className="h-5 w-5" strokeWidth={2} />
                </button>
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
                          prefetch={LINK_PREFETCH_DEFAULT}
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

  if (!portalReady) return null;
  return createPortal(menu, document.body);
}
