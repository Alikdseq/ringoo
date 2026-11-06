import type { Metadata } from 'next';
import { LegalDocLayout } from '@/components/legal/LegalDocLayout';
import { LEGAL_ORG, formatLegalAddress } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Реквизиты организации',
  description:
    'Реквизиты ИП Мисиков Герман Ростиславович: ИНН, ОГРНИП, адреса и контакты Ringoo во Владикавказе.',
  path: '/docs/requisites',
});

function displayValue(value: string, fallback: string): string {
  return value.trim() || fallback;
}

export default function RequisitesPage() {
  const inn = displayValue(LEGAL_ORG.inn, '—');
  const ogrnip = displayValue(LEGAL_ORG.ogrn, '—');
  const ogrnIssued = displayValue(LEGAL_ORG.ogrnIssuedAt, '');

  const REQUISITES = [
    { label: 'Наименование', value: LEGAL_ORG.legalName },
    { label: 'ИНН', value: inn },
    {
      label: 'ОГРНИП',
      value: ogrnIssued ? `${ogrnip} (выдан ${ogrnIssued} г.)` : ogrnip,
    },
    { label: 'Рег. номер СФР', value: displayValue(LEGAL_ORG.sfrRegNumber, '—') },
    { label: 'ОКВЭД', value: displayValue(LEGAL_ORG.okved, '—') },
    { label: 'ОКПО', value: displayValue(LEGAL_ORG.okpo, '—') },
    { label: 'Юридический адрес', value: formatLegalAddress() },
  ];

  const CONTACTS = [
    { label: 'Телефон', value: LEGAL_ORG.telephone },
    { label: 'Email', value: LEGAL_ORG.email },
    { label: 'Email по вопросам ПДн', value: LEGAL_ORG.privacyEmail },
  ];

  return (
    <LegalDocLayout
      title="Реквизиты организации"
      description="Юридические данные оператора персональных данных и продавца (ИП)."
    >
      <section>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Реквизиты</h2>
        <dl className="grid gap-3 sm:grid-cols-2">
          {REQUISITES.map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border bg-background-alt p-3">
              <dt className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
                {label}
              </dt>
              <dd className="mt-1 text-sm font-medium text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Фактические адреса</h2>
        <ul className="space-y-2">
          {LEGAL_ORG.actualAddresses.map(addr => (
            <li
              key={addr}
              className="rounded-lg border border-border bg-background-alt p-3 text-sm font-medium text-foreground"
            >
              {addr}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold text-foreground">Контакты</h2>
        <dl className="grid gap-3 sm:grid-cols-2">
          {CONTACTS.map(({ label, value }) => (
            <div key={label} className="rounded-lg border border-border bg-background-alt p-3">
              <dt className="text-xs font-medium uppercase tracking-wider text-foreground-muted">
                {label}
              </dt>
              <dd className="mt-1 text-sm font-medium text-foreground">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <p className="text-xs text-foreground-muted">
        Банковские реквизиты для безналичной оплаты предоставляются в счёте или по запросу.
        У индивидуального предпринимателя КПП не присваивается.
      </p>
    </LegalDocLayout>
  );
}
