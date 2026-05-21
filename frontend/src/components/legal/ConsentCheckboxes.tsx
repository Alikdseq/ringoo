'use client';

import Link from 'next/link';
import { LEGAL_DOC_LINKS } from '@/lib/legal/constants';
import { cn } from '@/lib/theme/utils';

export type ConsentCheckboxesProps = {
  consentPersonal: boolean;
  onConsentPersonalChange: (value: boolean) => void;
  consentOffer?: boolean;
  onConsentOfferChange?: (value: boolean) => void;
  consentMarketing: boolean;
  onConsentMarketingChange: (value: boolean) => void;
  showOffer?: boolean;
  showMarketing?: boolean;
  className?: string;
  /** Тёмная тема для футера */
  variant?: 'default' | 'dark';
};

const linkClass = 'font-medium underline';

export function ConsentCheckboxes({
  consentPersonal,
  onConsentPersonalChange,
  consentOffer = false,
  onConsentOfferChange,
  consentMarketing,
  onConsentMarketingChange,
  showOffer = false,
  showMarketing = true,
  className,
  variant = 'default',
}: ConsentCheckboxesProps) {
  const textMuted =
    variant === 'dark' ? 'text-zinc-400' : 'text-zinc-600 dark:text-zinc-400';
  const boxClass =
    variant === 'dark'
      ? 'border-zinc-600 bg-zinc-700/50'
      : 'border-border bg-zinc-50/80 dark:bg-zinc-900/40';
  const inputClass =
    variant === 'dark'
      ? 'border-zinc-500 bg-zinc-700 text-white focus:ring-zinc-400'
      : 'border-border';

  return (
    <div className={cn('space-y-3 rounded-lg border p-3 text-sm', boxClass, className)}>
      <label className="flex cursor-pointer items-start gap-2">
        <input
          type="checkbox"
          className={cn('mt-1 h-4 w-4 shrink-0 rounded', inputClass)}
          checked={consentPersonal}
          onChange={e => onConsentPersonalChange(e.target.checked)}
          required
          aria-describedby="consent-personal-label"
        />
        <span id="consent-personal-label" className={textMuted}>
          Я даю{' '}
          <Link
            href={LEGAL_DOC_LINKS.consent}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(linkClass, variant === 'dark' ? 'text-white' : 'text-primary')}
          >
            согласие на обработку персональных данных
          </Link>{' '}
          и ознакомлен(а) с{' '}
          <Link
            href={LEGAL_DOC_LINKS.privacy}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(linkClass, variant === 'dark' ? 'text-white' : 'text-primary')}
          >
            политикой конфиденциальности
          </Link>
          . <span className="text-danger">*</span>
        </span>
      </label>

      {showOffer && onConsentOfferChange ? (
        <label className="flex cursor-pointer items-start gap-2">
          <input
            type="checkbox"
            className={cn('mt-1 h-4 w-4 shrink-0 rounded', inputClass)}
            checked={consentOffer}
            onChange={e => onConsentOfferChange(e.target.checked)}
            required
            aria-describedby="consent-offer-label"
          />
          <span id="consent-offer-label" className={textMuted}>
            Я принимаю условия{' '}
            <Link
              href={LEGAL_DOC_LINKS.offer}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(linkClass, variant === 'dark' ? 'text-white' : 'text-primary')}
            >
              публичной оферты
            </Link>
            . <span className="text-danger">*</span>
          </span>
        </label>
      ) : null}

      {showMarketing ? (
        <label className="flex cursor-pointer items-start gap-2">
          <input
            type="checkbox"
            className={cn('mt-1 h-4 w-4 shrink-0 rounded', inputClass)}
            checked={consentMarketing}
            onChange={e => onConsentMarketingChange(e.target.checked)}
            aria-describedby="consent-marketing-label"
          />
          <span id="consent-marketing-label" className={textMuted}>
            Согласен(на) на{' '}
            <Link
              href={LEGAL_DOC_LINKS.marketing}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(linkClass, variant === 'dark' ? 'text-white' : 'text-primary')}
            >
              маркетинговые сообщения
            </Link>{' '}
            (необязательно).
          </span>
        </label>
      ) : null}
    </div>
  );
}
