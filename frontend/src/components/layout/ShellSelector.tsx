'use client';

import { usePathname } from 'next/navigation';
import type { Category } from '@/types';
import { AppShell } from '@/components/layout/AppShell';
import { AdminGuard } from '@/components/admin/AdminGuard';

interface ShellSelectorProps {
  children: React.ReactNode;
  initialCategories?: Category[];
}

export function ShellSelector({ children, initialCategories }: ShellSelectorProps) {
  const pathname = usePathname();
  const isAdmin = pathname?.startsWith('/admin');

  if (isAdmin) {
    return <AdminGuard>{children}</AdminGuard>;
  }

  return <AppShell initialCategories={initialCategories}>{children}</AppShell>;
}
