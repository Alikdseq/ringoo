import type { InputHTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

export interface InputProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'prefix' | 'suffix'
> {
  error?: string;
  prefix?: ReactNode;
  suffix?: ReactNode;
}

export function Input({ className, error, prefix, suffix, disabled, ...props }: InputProps) {
  return (
    <div className="space-y-1">
      <div
        className={clsx(
          'flex items-center gap-2 rounded-xl border bg-white px-3 py-2.5 text-sm',
          'border-border placeholder:text-foreground-subtle text-foreground',
          'focus-within:ring-2 focus-within:ring-brand focus-within:ring-offset-1 focus-within:border-brand',
          'transition-colors duration-150',
          disabled && 'opacity-60 cursor-not-allowed bg-zinc-50',
          error && 'border-danger focus-within:ring-danger',
          className
        )}
      >
        {prefix && <span className="text-foreground-subtle shrink-0">{prefix}</span>}
        <input
          className="w-full min-w-0 bg-transparent outline-none border-none text-foreground placeholder:text-foreground-subtle"
          disabled={disabled}
          {...props}
        />
        {suffix && <span className="text-foreground-subtle shrink-0">{suffix}</span>}
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
