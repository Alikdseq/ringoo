import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { CatalogContent } from '@/app/catalog/CatalogContent';
import { buildPageMetadata } from '@/lib/seo';
import {
  fetchBrandsServer,
  fetchCategoriesServer,
  fetchProductsServer,
} from '@/lib/api/services/products.service';

export const metadata: Metadata = buildPageMetadata({
  title: 'Каталог электроники — смартфоны, наушники, ноутбуки, аксессуары',
  description:
    'Купить технику в Ringoo: широкий ассортимент, цены, отзывы. Удобный поиск и фильтры. Рассрочка 0%, доставка за 2 часа.',
  path: '/catalog',
});

const FILTER_PARAMS = [
  'brand',
  'min_price',
  'max_price',
  'search',
  'in_stock',
  'ordering',
  'rating_min',
  'store',
  'page',
] as const;

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function CatalogPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const category = typeof sp.category === 'string' ? sp.category : undefined;

  if (category) {
    const hasOtherFilters = FILTER_PARAMS.some(key => {
      const val = sp[key];
      return val != null && val !== '';
    });
    if (!hasOtherFilters) {
      redirect(`/catalog/category/${encodeURIComponent(category)}`);
    }
  }

  const [initialProductsPage, initialCategories, initialBrands] = await Promise.all([
    fetchProductsServer({ page: 1, page_size: 24 }),
    fetchCategoriesServer(),
    fetchBrandsServer(),
  ]);

  return (
    <CatalogContent
      initialProductsPage={initialProductsPage}
      initialCategories={initialCategories}
      initialBrands={initialBrands}
    />
  );
}
