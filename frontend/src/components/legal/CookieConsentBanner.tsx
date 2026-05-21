'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { LEGAL_DOC_LINKS } from '@/lib/legal/constants';

type CookieConsentBannerProps = {
  onAccept: () => void;
  onReject: () => void;
};

export function CookieConsentBanner({ onAccept, onReject }: CookieConsentBannerProps) {
  return (
    <div
      role="dialog"
      aria-labelledby="cookie-banner-title"
      aria-live="polite"
      className="fixed inset-x-0 bottom-0 z-[100] border-t border-border bg-card/95 p-4 shadow-lg backdrop-blur-sm sm:bottom-4 sm:left-4 sm:right-auto sm:max-w-md sm:rounded-xl sm:border"
    >
      <p id="cookie-banner-title" className="mb-2 text-sm font-semibold text-foreground">
        Cookie и аналитика
      </p>
      <p className="mb-4 text-sm text-foreground-muted">
        Мы используем технические cookie для работы сайта и корзины. С вашего согласия подключается{' '}
        <strong>Яндекс.Метрика</strong> для статистики посещений. Подробнее — в{' '}
        <Link href={LEGAL_DOC_LINKS.cookies} className="underline hover:no-underline">
          политике cookie
        </Link>{' '}
        и{' '}
        <Link href={LEGAL_DOC_LINKS.privacy} className="underline hover:no-underline">
          политике конфиденциальности
        </Link>
        .
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" onClick={onAccept}>
          Принять
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={onReject}>
          Только необходимые
        </Button>
      </div>
    </div>
  );
}
