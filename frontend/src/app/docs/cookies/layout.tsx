import type { Metadata } from 'next';
import { LEGAL_DOC_LINKS } from '@/lib/legal/constants';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Политика cookie и веб-аналитики',
  description: 'Использование cookie и Яндекс.Метрики на сайте Ringoo.',
  path: LEGAL_DOC_LINKS.cookies,
});

export default function CookiesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
