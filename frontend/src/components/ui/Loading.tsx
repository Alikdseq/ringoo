import clsx from 'clsx';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const spinnerSize: Record<NonNullable<SpinnerProps['size']>, string> = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

export function Spinner({ size = 'md', className }: SpinnerProps) {
  return (
    <span
      className={clsx(
        'inline-block animate-spin rounded-full border-2 border-brand/30 border-t-brand',
        spinnerSize[size],
        className
      )}
      aria-hidden="true"
    />
  );
}

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={clsx('rounded-md bg-zinc-200 animate-skeleton-shimmer', className)} />;
}

export function Loading() {
  return (
    <div className="flex items-center justify-center p-8" aria-busy="true">
      <Spinner size="lg" />
    </div>
  );
}
