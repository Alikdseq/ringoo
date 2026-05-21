import type { Metadata } from 'next';
import { buildPageMetadata } from '@/lib/seo';
import { LEGAL_ORG, formatLegalAddress } from '@/lib/legal/constants';

export const metadata: Metadata = buildPageMetadata({
  title: 'Реквизиты организации',
  description: 'Юридический адрес, ИНН, ОГРН и контакты компании Ringoo во Владикавказе.',
  path: '/docs/requisites',
});

function displayValue(value: string, fallback: string): string {
  return value.trim() || fallback;
}

export default function RequisitesPage() {
  const inn = displayValue(LEGAL_ORG.inn, '— укажите NEXT_PUBLIC_ORG_INN в настройках окружения');
  const ogrn = displayValue(LEGAL_ORG.ogrn, '— укажите NEXT_PUBLIC_ORG_OGRN');
  const kpp = displayValue(LEGAL_ORG.kpp, '— при наличии: NEXT_PUBLIC_ORG_KPP');

  const REQUISITES = [
    { label: 'Наименование', value: LEGAL_ORG.legalName },
    { label: 'Юридический адрес', value: formatLegalAddress() },
    { label: 'ИНН', value: inn },
    { label: 'ОГРН', value: ogrn },
    { label: 'КПП', value: kpp },
    { label: 'Расчётный счёт', value: `По запросу на ${LEGAL_ORG.email}` },
  ];

  const CONTACTS = [
    { label: 'Телефон', value: LEGAL_ORG.telephone },
    { label: 'Email', value: LEGAL_ORG.email },
    { label: 'Email по вопросам ПДн', value: LEGAL_ORG.privacyEmail },
    {
      label: 'Адрес магазина',
      value: `г. ${LEGAL_ORG.address.addressLocality}, ${LEGAL_ORG.address.streetAddress}`,
    },
  ];

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="mb-2 text-2xl font-semibold text-foreground sm:text-3xl">
        Реквизиты организации
      </h1>
      <p className="mb-8 text-sm text-foreground-muted">
        Юридические данные оператора персональных данных и контакты для связи.
      </p>

      <div className="space-y-8">
        <section>
          <h2 className="mb-4 text-lg font-semibold text-foreground">Реквизиты компании</h2>
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
      </div>

      <p className="mt-8 text-xs text-foreground-muted">
        Для договоров и оплаты используйте реквизиты из счёта или запросите актуальную выписку у
        менеджера.
      </p>
    </div>
  );
}
