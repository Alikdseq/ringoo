import type { Metadata } from 'next';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Новости Ringoo',
  description: 'Новости сети магазинов Ringoo: акции, открытия, события во Владикавказе.',
  path: '/news',
  noIndex: true,
});

export default function NewsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
