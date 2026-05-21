import type { Metadata } from 'next';
import { buildPageMetadata } from '@/lib/seo';
import { SEO_GEO_CITY } from '@/lib/seo/constants';

export const metadata: Metadata = buildPageMetadata({
  title: `Рассрочка 0% на технику — калькулятор | Ringoo ${SEO_GEO_CITY}`,
  description:
    'Рассрочка без переплаты на смартфоны и электронику в Ringoo. Рассчитайте ежемесячный платёж онлайн. Самовывоз и доставка по Владикавказу.',
  path: '/installment',
});

export default function InstallmentLayout({ children }: { children: React.ReactNode }) {
  return children;
}
