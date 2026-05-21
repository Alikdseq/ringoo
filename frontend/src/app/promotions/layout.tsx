import type { Metadata } from 'next';
import { buildPageMetadata } from '@/lib/seo';

const monthYear = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' }).format(
  new Date()
);

export const metadata: Metadata = buildPageMetadata({
  title: `Акции и скидки Ringoo — спецпредложения ${monthYear}`,
  description:
    'Актуальные акции Ringoo: скидки на смартфоны и технику, рассрочка 0%, подарки. Самовывоз во Владикавказе, доставка по Осетии и России.',
  path: '/promotions',
});

export default function PromotionsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
