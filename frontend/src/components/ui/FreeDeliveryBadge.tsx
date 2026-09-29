import { Truck } from 'lucide-react';
import { cn } from '@/lib/theme/utils';

interface FreeDeliveryBadgeProps {
  className?: string;
  /** Компактный — без подзаголовка, для карточек товара/корзины */
  size?: 'sm' | 'md' | 'lg';
  /** Если false — без иконки */
  withIcon?: boolean;
}

const DELIVERY_TITLE = 'Доставка бесплатно от 100 ₽';
const DELIVERY_SUBTITLE = 'Привезём домой или на работу — куда удобно';

/**
 * Единый бейдж «Бесплатная доставка от 100 ₽» в фирменном emerald-стиле.
 * Используется на главной, в карточке товара, в корзине, в checkout.
 */
export function FreeDeliveryBadge({
  className,
  size = 'md',
  withIcon = true,
}: FreeDeliveryBadgeProps) {
  const pad =
    size === 'sm'
      ? 'gap-2 px-3 py-1.5 text-xs'
      : size === 'lg'
        ? 'gap-3 px-5 py-3 text-base'
        : 'gap-2.5 px-4 py-2 text-sm';
  const icon =
    size === 'sm' ? 'h-3.5 w-3.5' : size === 'lg' ? 'h-5 w-5' : 'h-4 w-4';

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 font-semibold text-emerald-800',
        pad,
        className
      )}
    >
      {withIcon && <Truck className={cn('shrink-0', icon)} aria-hidden />}
      <span>{DELIVERY_TITLE}</span>
    </span>
  );
}

interface FreeDeliveryCardProps {
  className?: string;
  variant?: 'card' | 'inline';
}

/**
 * Развёрнутый блок (карточка с подзаголовком) — для секций «о доставке».
 */
export function FreeDeliveryHighlight({ className, variant = 'card' }: FreeDeliveryCardProps) {
  return (
    <div
      className={cn(
        variant === 'card'
          ? 'rounded-2xl border border-emerald-200 bg-emerald-50/60 px-5 py-4'
          : 'flex',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-600/10 text-emerald-700">
          <Truck className="h-5 w-5" aria-hidden />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-emerald-900 sm:text-base">{DELIVERY_TITLE}</p>
          <p className="mt-0.5 text-xs text-emerald-800/85 sm:text-sm">{DELIVERY_SUBTITLE}</p>
        </div>
      </div>
    </div>
  );
}

export const FREE_DELIVERY_COPY = {
  title: DELIVERY_TITLE,
  subtitle: DELIVERY_SUBTITLE,
};
