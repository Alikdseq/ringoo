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
  LayoutGrid,
  BarChart3,
  Upload,
  Menu,
  X,
  HardDriveDownload,
} from 'lucide-react';
import { useAuth } from '@/lib/hooks/useAuth';
import { BrandLogo } from '@/components/layout/BrandLogo';
import { cn } from '@/lib/theme/utils';
import {
  canAccessAdminNav,
  type StaffAccessInfo,
} from '@/lib/admin/nav-access';

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
  { href: '/admin/backup', label: 'Резервное копирование', icon: HardDriveDownload },
];

function AdminSidebar({
  pathname,
  onNavigate,
  staffAccess,
}: {
  pathname: string | null;
  onNavigate?: () => void;
  staffAccess: StaffAccessInfo | null | undefined;
}) {
  const visibleNavItems = navItems.filter(item => canAccessAdminNav(item.href, staffAccess));

  return (
    <>
      <div className="flex h-[4.5rem] items-center border-b border-zinc-200 px-4">
        <Link
          href={visibleNavItems[0]?.href ?? '/admin/orders'}
          className="flex items-center gap-2"
          onClick={onNavigate}
        >
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
        {staffAccess && !staffAccess.is_superuser && (staffAccess.groups?.length ?? 0) === 0 ? (
          <p className="mt-3 px-3 text-xs text-amber-700">
            Нет групп ringoo_*. Обратитесь к суперпользователю за правами.
          </p>
        ) : null}
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

export function AdminLayout({
  children,
  staffAccess,
}: {
  children: React.ReactNode;
  staffAccess?: StaffAccessInfo | null;
}) {
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
        <AdminSidebar pathname={pathname} staffAccess={staffAccess} />
      </aside>

      {sidebarOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Закрыть меню"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col border-r border-zinc-200 bg-white shadow-xl">
            <div className="flex items-center justify-end border-b border-zinc-200 p-2">
              <button
                type="button"
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg"
                onClick={() => setSidebarOpen(false)}
                aria-label="Закрыть"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <AdminSidebar
              pathname={pathname}
              staffAccess={staffAccess}
              onNavigate={() => setSidebarOpen(false)}
            />
          </aside>
        </div>
      ) : null}

      <div className="flex min-h-screen flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-3 border-b border-zinc-200 bg-white px-4">
          <button
            type="button"
            className="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-lg border border-zinc-200 lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Открыть меню"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1 truncate text-sm text-zinc-600">
            {user?.phone ?? user?.email ?? 'Админ'}
          </div>
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-lg border border-zinc-200 px-3 text-sm text-zinc-700 hover:bg-zinc-50"
          >
            Выйти
          </button>
        </header>
        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
