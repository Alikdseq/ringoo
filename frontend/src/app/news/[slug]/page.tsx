import type { Metadata } from 'next';
import Link from 'next/link';
import { PlaceholderBlock } from '@/components/ui/PlaceholderBlock';
import { buildPageMetadata } from '@/lib/seo';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  return buildPageMetadata({
    title: `Новость: ${slug}`,
    description: 'Новости и события Ringoo.',
    path: `/news/${slug}`,
    noIndex: true,
  });
}

export default async function NewsArticlePage({ params }: PageProps) {
  const { slug } = await params;
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <p className="mb-2 text-xs text-foreground-muted">slug: {slug}</p>
      <h1 className="mb-2 text-2xl font-semibold text-foreground">Новость (шаблон)</h1>
      <p className="mb-6 text-sm text-foreground-muted">
        Полная страница новости: подключите публичный{' '}
        <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">GET /content/news/&lt;slug&gt;/</code> для
        контента и SEO, по аналогии с карточкой товара.
      </p>

      <div className="grid gap-4">
        <PlaceholderBlock title="Блок: обложка" note="Изображение новости." />
        <PlaceholderBlock title="Блок: текст" note="Полный HTML или rich text." />
      </div>

      <Link href="/news" className="mt-6 inline-flex text-sm text-info hover:underline">
        ← Все новости
      </Link>
    </div>
  );
}
