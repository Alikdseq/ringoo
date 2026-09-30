import { ORGANIZATION_CONTACT } from '@/lib/seo/constants';

/** Версия юридических документов (синхронизировать с backend POLICY_VERSION). */
export const POLICY_VERSION =
  process.env.NEXT_PUBLIC_POLICY_VERSION?.trim() || '2026-05-16';

export const LEGAL_ORG = {
  ...ORGANIZATION_CONTACT,
  inn: process.env.NEXT_PUBLIC_ORG_INN?.trim() || '',
  ogrn: process.env.NEXT_PUBLIC_ORG_OGRN?.trim() || '',
  kpp: process.env.NEXT_PUBLIC_ORG_KPP?.trim() || '',
  /** Ответственный за обработку ПДн / контакт для субъектов */
  privacyEmail:
    process.env.NEXT_PUBLIC_PRIVACY_EMAIL?.trim() || ORGANIZATION_CONTACT.email,
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
