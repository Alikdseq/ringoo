import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { forwardRef, cloneElement, isValidElement } from 'react';
import clsx from 'clsx';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'asChild'> {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
  loading?: boolean;
  asChild?: boolean;
}

const baseClasses =
  'inline-flex items-center justify-center rounded-full font-medium transition-all duration-150 ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--color-brand] focus-visible:ring-offset-2 ' +
  'disabled:opacity-60 disabled:cursor-not-allowed active:scale-[0.98]';

const variantClasses: Record<Variant, string> = {
  primary: 'bg-[var(--color-brand)] text-white hover:bg-[var(--color-brand-muted)]',
  secondary:
    'border border-border bg-white text-foreground hover:bg-zinc-100 focus-visible:ring-zinc-500',
  outline:
    'border border-zinc-800 bg-transparent text-zinc-900 hover:bg-zinc-900 hover:text-white focus-visible:ring-zinc-500',
  ghost: 'bg-transparent text-foreground hover:bg-zinc-100 focus-visible:ring-zinc-500',
};

const sizeClasses: Record<Size, string> = {
  sm: 'h-9 min-h-[44px] px-4 text-sm touch-manipulation sm:min-h-0',
  md: 'h-11 min-h-[44px] px-6 text-sm touch-manipulation sm:min-h-0',
  lg: 'h-12 min-h-[44px] px-8 text-base touch-manipulation sm:min-h-0',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { children, variant = 'primary', size = 'md', fullWidth, loading, asChild, className, ...props },
  ref
) {
  const isDisabled = props.disabled || loading;
  const classes = clsx(
    baseClasses,
    variantClasses[variant],
    sizeClasses[size],
    fullWidth && 'w-full',
    className
  );

  if (asChild && isValidElement(children)) {
    return cloneElement(children as React.ReactElement<{ className?: string }>, {
      className: clsx(
        classes,
        (children as React.ReactElement<{ className?: string }>).props.className
      ),
    });
  }

  return (
    <button
      ref={ref}
      className={classes}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <span
          className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent opacity-70"
          aria-hidden="true"
        />
      )}
      {children}
    </button>
  );
});
