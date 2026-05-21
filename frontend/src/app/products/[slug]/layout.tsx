import type { ReactNode } from 'react';
import type { Metadata } from 'next';
import { fetchProductDetailServer } from '@/lib/api/services/products.service';
import { buildPageMetadata, truncateDescription } from '@/lib/seo';
import { getMediaUrl } from '@/lib/image-url';
import { SEO_GEO_CITY } from '@/lib/seo/constants';

type LayoutProps = {
  children: ReactNode;
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: LayoutProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await fetchProductDetailServer(slug);

  if (!product) {
    return buildPageMetadata({
      title: 'Товар не найден',
      path: `/products/${slug}`,
      noIndex: true,
    });
  }

  const price = product.price ? Math.round(Number(product.price)) : null;
  const title =
    product.meta_title?.trim() ||
    (price
      ? `${product.title} купить в ${SEO_GEO_CITY} — ${price} ₽`
      : `${product.title} купить в ${SEO_GEO_CITY}`);

  const description =
    product.meta_description?.trim() ||
    product.short_description?.trim() ||
    `${product.title} в наличии в Ringoo. Официальная гарантия, самовывоз в ${SEO_GEO_CITY}, доставка по России.`;

  const mainImage = product.images?.find(i => i.is_main) ?? product.images?.[0];
  const ogImage = mainImage?.image ? getMediaUrl(mainImage.image) : undefined;

  return buildPageMetadata({
    title,
    description: truncateDescription(description),
    path: `/products/${slug}`,
    ogImage,
  });
}

export default function ProductSlugLayout({ children }: LayoutProps) {
  return children;
}
