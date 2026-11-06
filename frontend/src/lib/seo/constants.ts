import { getSiteUrl } from '@/lib/site-url';

export const SEO_BRAND = 'Ringoo';
export const SEO_BRAND_SUFFIX = `| ${SEO_BRAND}`;
export const SEO_GEO_CITY = 'Владикавказ';
export const SEO_GEO_REGION = 'Северная Осетия';

export const DEFAULT_OG_IMAGE_PATH = '/fon/fon.jpg';

export function getDefaultOgImageUrl(): string {
  return new URL(DEFAULT_OG_IMAGE_PATH, getSiteUrl()).toString();
}

export const ORGANIZATION_CONTACT = {
  name: SEO_BRAND,
  /** Юридическое наименование оператора (ИП). */
  legalName: 'ИП Мисиков Герман Ростиславович',
  url: getSiteUrl(),
  telephone: '+7 (918) 415-77-88',
  email: 'misikov.german@mail.ru',
  /** Юридический адрес регистрации */
  address: {
    streetAddress: 'ул. Карцинское шоссе, д. 5, кв. 58',
    addressLocality: SEO_GEO_CITY,
    addressRegion: 'РСО-Алания',
    postalCode: '362002',
    addressCountry: 'RU',
  },
} as const;
