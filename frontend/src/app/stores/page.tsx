import type { Metadata } from 'next';
import { StoresContent } from '@/app/stores/StoresContent';
import { buildPageMetadata } from '@/lib/seo';

export const metadata: Metadata = buildPageMetadata({
  title: 'Магазины Ringoo во Владикавказе и Осетии — адреса, время работы, наличие товаров',
  description:
    'Ближайший магазин Ringoo: адреса, телефоны, график работы. Проверьте наличие товара и заберите сегодня. Карта магазинов, маршрут онлайн.',
  path: '/stores',
});

export default function StoresPage() {
  return <StoresContent />;
}
