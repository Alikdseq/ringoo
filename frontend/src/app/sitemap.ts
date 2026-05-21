import type { MetadataRoute } from 'next';
import { getApiV1BaseUrl, getSiteUrl } from '@/lib/site-url';

const REVALIDATE = 3600;

const STATIC_PATHS = [
  '/',
  '/catalog',
  '/promotions',
  '/installment',
  '/stores',
  '/about',
  '/order-status',
  '/site-map',
  '/docs/requisites',
  '/docs/offer',
  '/docs/privacy',
  '/docs/consent',
  '/docs/marketing-consent',
  '/docs/cookies',
] as const;

interface Paginated<T> {
  next: string | null;
  results: T[];
}

async function fetchAllPages<T>(
  initialPath: string,
  pick: (row: T) => string | null | undefined
): Promise<string[]> {
  const api = getApiV1BaseUrl();
  const out: string[] = [];
  let url: string | null = `${api}${initialPath}`;
  try {
    while (url) {
      const res = await fetch(url, { next: { revalidate: REVALIDATE } });
      if (!res.ok) break;
      const data = (await res.json()) as Paginated<T>;
      for (const row of data.results ?? []) {
        const s = pick(row);
        if (s) out.push(s);
      }
      url = data.next;
    }
  } catch {
    /* API недоступен на сборке — остаются только статические URL */
  }
  return out;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = getSiteUrl();
  const now = new Date();

  const staticEntries: MetadataRoute.Sitemap = STATIC_PATHS.map(path => ({
    url: `${base}${path === '/' ? '' : path}`,
    lastModified: now,
    changeFrequency: path === '/' ? 'daily' : 'weekly',
    priority: path === '/' ? 1 : 0.7,
  }));

  const [productSlugs, categorySlugs, storeSlugs] = await Promise.all([
    fetchAllPages<{ slug?: string }>('/products/products/?page_size=100', p => p.slug ?? null),
    fetchAllPages<{ slug?: string }>('/products/categories/?page_size=100', c =>
      c.slug ? c.slug : null
    ),
    fetchAllPages<{ slug?: string; is_active?: boolean }>(
      '/stores/?page_size=100&is_active=true',
      s => (s.is_active !== false && s.slug ? s.slug : null)
    ),
  ]);

  const productEntries: MetadataRoute.Sitemap = productSlugs.map(slug => ({
    url: `${base}/products/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.8,
  }));

  const categoryEntries: MetadataRoute.Sitemap = categorySlugs.map(slug => ({
    url: `${base}/catalog/category/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.75,
  }));

  const storeEntries: MetadataRoute.Sitemap = storeSlugs.map(slug => ({
    url: `${base}/stores/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.75,
  }));

  return [...staticEntries, ...categoryEntries, ...productEntries, ...storeEntries];
}
