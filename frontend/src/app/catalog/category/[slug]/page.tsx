import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import {
  fetchBrandsServer,
  fetchCategoriesServer,
  fetchCategoryBySlugServer,
  fetchProductsServer,
} from '@/lib/api/services/products.service';
import { CatalogContent } from '@/app/catalog/CatalogContent';
import {
  JsonLd,
  buildPageMetadata,
  categoryPageJsonLd,
  truncateDescription,
} from '@/lib/seo';
import { SEO_GEO_CITY } from '@/lib/seo/constants';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const category = await fetchCategoryBySlugServer(slug);
  if (!category) {
    return buildPageMetadata({
      title: 'Категория не найдена',
      path: `/catalog/category/${slug}`,
      noIndex: true,
    });
  }

  const title =
    category.meta_title?.trim() ||
    `Купить ${category.title} в ${SEO_GEO_CITY} — цены, наличие`;
  const description =
    category.meta_description?.trim() ||
    `${category.title} в Ringoo: официальная техника, гарантия, рассрочка 0%, самовывоз в ${SEO_GEO_CITY} и доставка по России.`;

  return buildPageMetadata({
    title,
    description: truncateDescription(description),
    path: `/catalog/category/${slug}`,
  });
}

export default async function CatalogCategoryPage({ params }: PageProps) {
  const { slug } = await params;
  const category = await fetchCategoryBySlugServer(slug);
  if (!category) notFound();

  const [initialProductsPage, initialCategories, initialBrands] = await Promise.all([
    fetchProductsServer({
      category: slug,
      page_size: 24,
      page: 1,
    }),
    fetchCategoriesServer(),
    fetchBrandsServer(),
  ]);

  return (
    <>
      <JsonLd data={categoryPageJsonLd(category, initialProductsPage.results)} />
      <CatalogContent
        categorySlugFromPath={slug}
        initialProductsPage={initialProductsPage}
        initialCategories={initialCategories}
        initialBrands={initialBrands}
      />
    </>
  );
}
