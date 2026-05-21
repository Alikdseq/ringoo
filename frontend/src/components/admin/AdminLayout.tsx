'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ShoppingCart,
  UserCircle,
  Package,
  Layers,
  Users,
  FileText,
  Store,
  Tag,
  MessageSquare,
  LogOut,
  LayoutGrid,
  BarChart3,
  Upload,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import { BrandLogo } from '@/components/layout/BrandLogo';
import { cn } from '@/lib/theme/utils';

const ADMIN_NAV_HIDDEN_HREFS = new Set(['/admin', '/admin/content', '/admin/analytics']);

const navItems = [
  { href: '/admin/orders', label: 'Заказы', icon: ShoppingCart },
  { href: '/admin/products', label: 'Товары', icon: Package },
  { href: '/admin/products/import', label: 'Импорт XLSX', icon: Upload },
  { href: '/admin/categories', label: 'Категории', icon: Layers },
  { href: '/admin/stock', label: 'Остатки', icon: LayoutGrid },
  { href: '/admin/users', label: 'Пользователи', icon: Users },
  { href: '/admin/content', label: 'Контент', icon: FileText },
  { href: '/admin/stores', label: 'Магазины', icon: Store },
  { href: '/admin/managers', label: 'Менеджеры', icon: UserCircle },
  { href: '/admin/promotions', label: 'Акции', icon: Tag },
  { href: '/admin/crm', label: 'Заявки (CRM)', icon: MessageSquare },
  { href: '/admin/analytics', label: 'Аналитика', icon: BarChart3 },
];

function AdminSidebar({
  pathname,
  onNavigate,
}: {
  pathname: string | null;
  onNavigate?: () => void;
}) {
  const visibleNavItems = navItems.filter(item => !ADMIN_NAV_HIDDEN_HREFS.has(item.href));

  return (
    <>
      <div className="flex h-[4.5rem] items-center border-b border-zinc-200 px-4">
        <Link href="/admin/orders" className="flex items-center gap-2" onClick={onNavigate}>
          <BrandLogo link={false} height={48} width={100} />
          <span className="text-sm font-semibold text-zinc-600">Admin</span>
        </Link>
      </div>
      <nav className="flex-1 overflow-y-auto p-3" aria-label="Меню админки">
        <ul className="space-y-0.5">
          {visibleNavItems.map(item => {
            const isActive =
              item.href === '/admin'
                ? pathname === '/admin'
                : item.href === '/admin/products'
                  ? pathname === '/admin/products' ||
                    (pathname?.startsWith('/admin/products/') &&
                      !pathname.startsWith('/admin/products/import'))
                  : pathname === item.href || pathname?.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    'flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors touch-manipulation lg:min-h-0',
                    isActive
                      ? 'bg-[var(--color-brand)] text-white'
                      : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900'
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="border-t border-zinc-200 p-3">
        <Link
          href="/"
          onClick={onNavigate}
          className="flex min-h-[44px] items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 lg:min-h-0"
        >
          ← На сайт
        </Link>
      </div>
    </>
  );
}

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!sidebarOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [sidebarOpen]);

  const handleLogout = async () => {
    await logout();
    router.replace('/admin/login');
  };

  return (
    <div className="flex min-h-screen bg-zinc-100">
      <aside className="fixed left-0 top-0 z-30 hidden h-full w-64 flex-col border-r border-zinc-200 bg-white lg:flex">
        <AdminSidebar pathname={pathname} />
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Закрыть меню"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="relative flex h-full w-[min(100vw,280px)] flex-col border-r border-zinc-200 bg-white shadow-xl">
            <button
              type="button"
              className="absolute right-3 top-3 inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg hover:bg-zinc-100"
              aria-label="Закрыть"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </button>
            <AdminSidebar pathname={pathname} onNavigate={() => setSidebarOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="flex min-h-screen w-full flex-1 flex-col lg:ml-64">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-2 border-b border-zinc-200 bg-white px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg border border-zinc-200 lg:hidden"
              aria-label="Открыть меню"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="truncate text-sm text-zinc-500">
              {user?.phone || user?.email || 'Администратор'}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex min-h-[44px] shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-600 transition-colors hover:bg-zinc-100 hover:text-zinc-900 touch-manipulation sm:min-h-0"
            aria-label="Выйти"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Выйти</span>
          </button>
        </header>

        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
