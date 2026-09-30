import { getSiteUrl } from '@/lib/site-url';
import { getMediaUrl } from '@/lib/image-url';
import { ORGANIZATION_CONTACT } from './constants';
import type { Category, Product, ProductDetail } from '@/types';
import type { StorePage } from '@/lib/api/services/stores.service';

type JsonLdProps = {
  data: Record<string, unknown> | Record<string, unknown>[];
};

export function JsonLd({ data }: JsonLdProps) {
  const payload = Array.isArray(data) ? data : [data];
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(payload.length === 1 ? payload[0] : payload) }}
    />
  );
}

export function organizationJsonLd() {
  const site = getSiteUrl();
  const { address, ...org } = ORGANIZATION_CONTACT;
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: org.name,
    legalName: org.legalName,
    url: site,
    email: org.email,
    telephone: org.telephone,
    address: {
      '@type': 'PostalAddress',
      ...address,
    },
  };
}

export function webSiteJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: ORGANIZATION_CONTACT.name,
    url: getSiteUrl(),
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${getSiteUrl()}/catalog?search={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  };
}

export function breadcrumbJsonLd(items: { name: string; path: string }[]) {
  const base = getSiteUrl();
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: `${base}${item.path.startsWith('/') ? item.path : `/${item.path}`}`,
    })),
  };
}

export function productJsonLd(product: ProductDetail, slug: string) {
  const mainImage = product.images?.find(i => i.is_main) ?? product.images?.[0];
  const imageUrl = mainImage?.image ? getMediaUrl(mainImage.image) : undefined;
  const inStock = product.availability_status !== 'out_of_stock';
  const price = product.price ? Number(product.price) : undefined;

  return {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.title,
    description:
      product.meta_description?.trim() ||
      product.short_description?.trim() ||
      product.description?.replace(/<[^>]*>/g, '').slice(0, 500),
    sku: product.sku,
    brand: product.brand ? { '@type': 'Brand', name: product.brand } : undefined,
    image: imageUrl ? [imageUrl] : undefined,
    offers: {
      '@type': 'Offer',
      url: `${getSiteUrl()}/products/${slug}`,
      priceCurrency: 'RUB',
      price: price && Number.isFinite(price) ? price : undefined,
      availability: inStock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
  };
}

export function itemListJsonLd(products: Product[], listPath: string) {
  const base = getSiteUrl();
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemList',
    url: `${base}${listPath}`,
    numberOfItems: products.length,
    itemListElement: products.map((p, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      url: `${base}/products/${p.slug}`,
      name: p.title,
    })),
  };
}

export function localBusinessJsonLd(store: StorePage) {
  const lat = store.coordinates?.latitude ? Number(store.coordinates.latitude) : undefined;
  const lng = store.coordinates?.longitude ? Number(store.coordinates.longitude) : undefined;
  const hours = store.working_hours
    ? Object.entries(store.working_hours).map(([day, hours]) => `${day} ${hours}`)
    : undefined;

  return {
    '@context': 'https://schema.org',
    '@type': 'Store',
    name: store.name,
    description: store.description || store.meta_description || undefined,
    url: `${getSiteUrl()}/stores/${store.slug}`,
    telephone: store.phone || undefined,
    email: store.email || undefined,
    address: {
      '@type': 'PostalAddress',
      streetAddress: store.address,
      addressLocality: store.city,
      addressCountry: 'RU',
    },
    geo:
      lat != null && lng != null && Number.isFinite(lat) && Number.isFinite(lng)
        ? { '@type': 'GeoCoordinates', latitude: lat, longitude: lng }
        : undefined,
    openingHours: hours,
  };
}

export function categoryPageJsonLd(category: Category, products: Product[]) {
  const path = `/catalog/category/${category.slug}`;
  return [
    breadcrumbJsonLd([
      { name: 'Главная', path: '/' },
      { name: 'Каталог', path: '/catalog' },
      { name: category.title, path },
    ]),
    itemListJsonLd(products, path),
  ];
}
