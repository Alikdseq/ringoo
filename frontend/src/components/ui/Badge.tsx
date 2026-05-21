import clsx from 'clsx';

type BadgeVariant = 'discount' | 'success' | 'info';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  discount: 'bg-danger text-white',
  success: 'bg-brand text-white',
  info: 'bg-[var(--color-info)] text-white',
};

export function Badge({ children, variant = 'discount', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

/** Бейдж скидки: −X% (DESIGN_SPEC §5) */
export function DiscountBadge({ percent }: { percent: number }) {
  return (
    <Badge variant="discount" className="absolute right-2 top-2">
      −{percent}%
    </Badge>
  );
}
