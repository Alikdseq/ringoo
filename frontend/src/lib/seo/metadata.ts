import type { Metadata } from 'next';
import { getSiteUrl } from '@/lib/site-url';
import { getDefaultOgImageUrl, SEO_BRAND, SEO_BRAND_SUFFIX } from './constants';

export type PageMetadataInput = {
  title: string;
  description?: string;
  path?: string;
  noIndex?: boolean;
  ogImage?: string | null;
  ogType?: 'website' | 'article';
};

function absoluteUrl(path: string): string {
  const base = getSiteUrl();
  if (path.startsWith('http')) return path;
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

export function formatTitle(title: string, options?: { withBrand?: boolean; brandFirst?: boolean }): string {
  const trimmed = title.trim();
  if (!trimmed) return SEO_BRAND;
  const withBrand = options?.withBrand !== false;
  if (!withBrand) return trimmed;
  if (trimmed.includes(SEO_BRAND)) return trimmed;
  if (options?.brandFirst) return `${SEO_BRAND} — ${trimmed}`;
  return `${trimmed} ${SEO_BRAND_SUFFIX}`;
}

export function truncateDescription(text: string | null | undefined, max = 160): string | undefined {
  if (!text?.trim()) return undefined;
  const plain = text.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
  if (!plain) return undefined;
  return plain.length <= max ? plain : `${plain.slice(0, max - 1)}…`;
}

export function buildPageMetadata(input: PageMetadataInput): Metadata {
  const title = formatTitle(input.title);
  const description = truncateDescription(input.description);
  const canonicalPath = input.path ?? '/';
  const ogImage = input.ogImage ? absoluteUrl(input.ogImage) : getDefaultOgImageUrl();

  return {
    title: { absolute: title },
    description,
    alternates: {
      canonical: canonicalPath,
    },
    robots: input.noIndex
      ? { index: false, follow: true }
      : { index: true, follow: true },
    openGraph: {
      title,
      description,
      url: absoluteUrl(canonicalPath),
      siteName: SEO_BRAND,
      locale: 'ru_RU',
      type: input.ogType ?? 'website',
      images: [{ url: ogImage, width: 1200, height: 630, alt: SEO_BRAND }],
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [ogImage],
    },
  };
}

export function buildRootMetadata(): Metadata {
  return {
    metadataBase: new URL(getSiteUrl()),
    title: {
      default: SEO_BRAND,
      template: `%s ${SEO_BRAND_SUFFIX}`,
    },
    description: 'Интернет-магазин электроники Ringoo во Владикавказе и Северной Осетии.',
    openGraph: {
      siteName: SEO_BRAND,
      locale: 'ru_RU',
      type: 'website',
      images: [{ url: getDefaultOgImageUrl(), width: 1200, height: 630, alt: SEO_BRAND }],
    },
    twitter: {
      card: 'summary_large_image',
    },
  };
}
