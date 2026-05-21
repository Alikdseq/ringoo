import type { ReactNode } from 'react';
import { CONTAINER_CLASS, CONTAINER_WIDE_CLASS } from '@/lib/theme/spacing';
import { cn } from '@/lib/theme/utils';

interface PageContainerProps {
  children: ReactNode;
  className?: string;
  /** Каталог, акции — чуть шире (max-w-7xl) */
  wide?: boolean;
  as?: 'div' | 'section' | 'main';
}

export function PageContainer({
  children,
  className,
  wide = false,
  as: Tag = 'div',
}: PageContainerProps) {
  return (
    <Tag className={cn(wide ? CONTAINER_WIDE_CLASS : CONTAINER_CLASS, className)}>
      {children}
    </Tag>
  );
}
