import type { HTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

type CardVariant = 'default' | 'ghost' | 'interactive';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: CardVariant;
}

export function Card({ children, className, variant = 'default', ...props }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-border bg-white p-4 transition-all duration-150 ease-out',
        variant === 'ghost' && 'border-transparent bg-transparent shadow-none',
        variant === 'interactive' && 'cursor-pointer hover:-translate-y-0.5',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
