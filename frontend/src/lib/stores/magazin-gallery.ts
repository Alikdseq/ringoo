import type { PageGalleryImage } from '@/lib/api/services/pageGallery.service';

/** Загружает manifest из public/magazins/manifest.json (генерируется скриптом). */
export async function fetchMagazinGalleryUrls(): Promise<string[]> {
  try {
    const res = await fetch('/magazins/manifest.json', { cache: 'force-cache' });
    if (!res.ok) return [];
    const data = (await res.json()) as { images?: string[] };
    return Array.isArray(data.images) ? data.images : [];
  } catch {
    return [];
  }
}

export function magazinUrlsToGalleryImages(urls: string[]): PageGalleryImage[] {
  return urls.map((src, index) => ({
    id: `magazin-static-${index}`,
    placement: 'stores_hero' as const,
    image: src,
    alt_text: `Магазин Ringoo ${index + 1}`,
    sort_order: index,
  }));
}
