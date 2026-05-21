import Link from 'next/link';
import { LEGAL_DOC_LINKS, POLICY_VERSION } from '@/lib/legal/constants';

const RELATED = [
  { href: LEGAL_DOC_LINKS.privacy, label: 'Политика конфиденциальности' },
  { href: LEGAL_DOC_LINKS.consent, label: 'Согласие на обработку ПДн' },
  { href: LEGAL_DOC_LINKS.marketing, label: 'Согласие на маркетинг' },
  { href: LEGAL_DOC_LINKS.cookies, label: 'Cookie и аналитика' },
  { href: LEGAL_DOC_LINKS.offer, label: 'Публичная оферта' },
  { href: LEGAL_DOC_LINKS.requisites, label: 'Реквизиты' },
] as const;

type LegalDocLayoutProps = {
  title: string;
  description?: string;
  children: React.ReactNode;
};

export function LegalDocLayout({ title, description, children }: LegalDocLayoutProps) {
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-2xl font-semibold text-foreground sm:text-3xl">{title}</h1>
      {description ? (
        <p className="mb-2 text-sm text-foreground-muted">{description}</p>
      ) : null}
      <p className="mb-8 text-sm text-foreground-muted">Версия документа: {POLICY_VERSION}</p>
      <div className="prose prose-zinc max-w-none space-y-8 text-sm dark:prose-invert">
        {children}
      </div>
      <nav className="mt-10 border-t border-border pt-6">
        <p className="mb-3 text-xs font-medium uppercase tracking-wider text-foreground-muted">
          Связанные документы
        </p>
        <ul className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {RELATED.map(({ href, label }) => (
            <li key={href}>
              <Link href={href} className="text-[var(--color-brand)] underline">
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
