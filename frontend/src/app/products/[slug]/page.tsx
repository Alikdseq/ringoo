import { notFound } from 'next/navigation';
import { fetchProductDetailServer } from '@/lib/api/services/products.service';
import { JsonLd, breadcrumbJsonLd, productJsonLd } from '@/lib/seo';
import { ProductPageClient } from './ProductPageClient';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export default async function ProductPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await fetchProductDetailServer(slug);

  if (!product || product.is_active === false) {
    notFound();
  }

  const categorySlug = product.category?.slug;
  const breadcrumbItems = [
    { name: 'Главная', path: '/' },
    { name: 'Каталог', path: '/catalog' },
    ...(product.category
      ? [
          {
            name: product.category.title,
            path: categorySlug
              ? `/catalog/category/${categorySlug}`
              : '/catalog',
          },
        ]
      : []),
    { name: product.title, path: `/products/${slug}` },
  ];

  return (
    <>
      <JsonLd data={[productJsonLd(product, slug), breadcrumbJsonLd(breadcrumbItems)]} />
      <ProductPageClient slug={slug} initialProduct={product} />
    </>
  );
}
