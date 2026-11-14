import type { MetadataRoute } from 'next';
import { buildInternalDjangoFetchInit } from '@/lib/api/server-fetch';
import { PUBLIC_INDEXABLE_STATIC_ROUTES } from '@/lib/seo/public-site-routes';
import { getApiV1BaseUrl, getSiteUrl } from '@/lib/site-url';

const REVALIDATE = 3600;

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
      const res = await fetch(
        url,
        buildInternalDjangoFetchInit({ next: { revalidate: REVALIDATE } })
      );
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

  const staticEntries: MetadataRoute.Sitemap = PUBLIC_INDEXABLE_STATIC_ROUTES.map(
    route => ({
      url: `${base}${route.path === '/' ? '' : route.path}`,
      lastModified: now,
      changeFrequency: route.changeFrequency ?? 'weekly',
      priority: route.priority ?? 0.7,
    })
  );

  const [productSlugs, categorySlugs, storeSlugs, articleSlugs, newsSlugs] =
    await Promise.all([
      fetchAllPages<{ slug?: string }>('/products/products/?page_size=100', p => p.slug ?? null),
      fetchAllPages<{ slug?: string }>('/products/categories/?page_size=100', c =>
        c.slug ? c.slug : null
      ),
      fetchAllPages<{ slug?: string; is_active?: boolean }>(
        '/stores/?page_size=100&is_active=true',
        s => (s.is_active !== false && s.slug ? s.slug : null)
      ),
      fetchAllPages<{ slug?: string }>('/content/articles/?page_size=100', a => a.slug ?? null),
      fetchAllPages<{ slug?: string }>('/content/news/?page_size=100', n => n.slug ?? null),
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

  const articleEntries: MetadataRoute.Sitemap = articleSlugs.map(slug => ({
    url: `${base}/blog/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.65,
  }));

  const newsEntries: MetadataRoute.Sitemap = newsSlugs.map(slug => ({
    url: `${base}/news/${slug}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.65,
  }));

  return [
    ...staticEntries,
    ...categoryEntries,
    ...productEntries,
    ...storeEntries,
    ...articleEntries,
    ...newsEntries,
  ];
}
