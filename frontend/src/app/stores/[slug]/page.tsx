import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { fetchStoreBySlugServer } from '@/lib/api/services/stores.service';
import { StoreDetailContent } from '@/app/stores/[slug]/StoreDetailContent';
import { JsonLd, buildPageMetadata, breadcrumbJsonLd, localBusinessJsonLd, truncateDescription } from '@/lib/seo';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const store = await fetchStoreBySlugServer(slug);
  if (!store) {
    return buildPageMetadata({
      title: 'Магазин не найден',
      path: `/stores/${slug}`,
      noIndex: true,
    });
  }
  const title =
    store.meta_title?.trim() || `Магазин Ringoo — ${store.address}, ${store.city}`;
  const description =
    store.meta_description?.trim() ||
    store.description?.slice(0, 160) ||
    `Ringoo на ${store.address}: смартфоны и техника в наличии. Часы работы, самовывоз, консультация менеджера.`;

  return buildPageMetadata({
    title,
    description: truncateDescription(description),
    path: `/stores/${slug}`,
  });
}

export default async function StoreBySlugPage({ params }: PageProps) {
  const { slug } = await params;
  const store = await fetchStoreBySlugServer(slug);
  if (!store) notFound();

  return (
    <>
      <JsonLd
        data={[
          localBusinessJsonLd(store),
          breadcrumbJsonLd([
            { name: 'Главная', path: '/' },
            { name: 'Магазины', path: '/stores' },
            { name: store.name, path: `/stores/${slug}` },
          ]),
        ]}
      />
      <StoreDetailContent slug={slug} initialStore={store} />
    </>
  );
}
