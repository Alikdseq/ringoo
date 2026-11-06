import { ORGANIZATION_CONTACT } from '@/lib/seo/constants';

/** Версия юридических документов (синхронизировать с backend POLICY_VERSION). */
/** Дата редакции юридических текстов сайта (YYYY-MM-DD). */
export const POLICY_VERSION = process.env.NEXT_PUBLIC_POLICY_VERSION?.trim() || '2026-11-03';

/**
 * Реквизиты оператора. Env перекрывает значения по умолчанию
 * (удобно для staging/prod без правки кода).
 */
export const LEGAL_ORG = {
  ...ORGANIZATION_CONTACT,
  inn: process.env.NEXT_PUBLIC_ORG_INN?.trim() || '151502153141',
  /** Для ИП — ОГРНИП */
  ogrn: process.env.NEXT_PUBLIC_ORG_OGRN?.trim() || '308151508700014',
  ogrnIssuedAt: process.env.NEXT_PUBLIC_ORG_OGRN_ISSUED_AT?.trim() || '27.03.2008',
  /** У ИП КПП нет */
  kpp: process.env.NEXT_PUBLIC_ORG_KPP?.trim() || '',
  sfrRegNumber: process.env.NEXT_PUBLIC_ORG_SFR?.trim() || '1210189435',
  okved: process.env.NEXT_PUBLIC_ORG_OKVED?.trim() || '47.78',
  okpo: process.env.NEXT_PUBLIC_ORG_OKPO?.trim() || '0156586320',
  /** Фактические адреса точек / магазинов */
  actualAddresses: [
    'РСО-Алания, г. Владикавказ, ул. Доватора, д. 5',
    'РСО-Алания, г. Владикавказ, ул. Кирова, д. 41',
  ] as const,
  privacyEmail: process.env.NEXT_PUBLIC_PRIVACY_EMAIL?.trim() || ORGANIZATION_CONTACT.email,
} as const;

export const LEGAL_DOC_LINKS = {
  privacy: '/docs/privacy',
  consent: '/docs/consent',
  marketing: '/docs/marketing-consent',
  cookies: '/docs/cookies',
  offer: '/docs/offer',
  requisites: '/docs/requisites',
} as const;

export function formatLegalAddress(): string {
  const a = LEGAL_ORG.address;
  return `${a.postalCode}, ${a.addressRegion}, г. ${a.addressLocality}, ${a.streetAddress}`;
}
