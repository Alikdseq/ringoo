import type { Metadata } from 'next';
import { AboutContent } from './AboutContent';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'О компании Ringoo — сеть магазинов электроники в Осетии',
  description:
    'Узнайте о нашей команде, миссии и магазинах. Рейтинг 4.7, отзывы покупателей, карта магазинов. Ringoo — техника с душой.',
  path: '/about',
});

export default function AboutPage() {
  return <AboutContent />;
}
