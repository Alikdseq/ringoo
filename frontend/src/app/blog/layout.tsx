import type { Metadata } from 'next';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Блог Ringoo — обзоры и советы по электронике',
  description:
    'Статьи Ringoo: обзоры смартфонов, сравнения, советы по выбору техники и сервису во Владикавказе.',
  path: '/blog',
  noIndex: true,
});

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
