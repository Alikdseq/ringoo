import type { ReactNode } from 'react';
import { ADMIN_TABLE_SCROLL_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';

export function AdminTableScroll({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn(ADMIN_TABLE_SCROLL_CLASS, className)}>{children}</div>;
}
