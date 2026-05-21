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
    title: `Статья: ${slug}`,
    description: 'Материал блога Ringoo: электроника, доставка, сервис.',
    path: `/blog/${slug}`,
    noIndex: true,
  });
}

export default async function BlogArticlePage({ params }: PageProps) {
  const { slug } = await params;
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <p className="mb-2 text-xs text-foreground-muted">slug: {slug}</p>
      <h1 className="mb-2 text-2xl font-semibold text-foreground">Статья блога (шаблон)</h1>
      <p className="mb-6 text-sm text-foreground-muted">
        Тут будет полноценная страница статьи с контентом и дополнительными блоками.
      </p>

      <div className="grid gap-4">
        <PlaceholderBlock title="Блок: Обложка статьи" note="Тут будет hero-изображение статьи." />
        <PlaceholderBlock
          title="Блок: Метаданные"
          note="Тут будут дата, автор, категория, теги и время чтения."
        />
        <PlaceholderBlock
          title="Блок: Контент статьи"
          note="Тут будет rich content (заголовки, абзацы, цитаты, изображения)."
        />
        <PlaceholderBlock
          title="Блок: Похожие статьи"
          note="Тут будут карточки материалов по теме."
        />
      </div>

      <Link href="/blog" className="mt-6 inline-flex text-sm text-info hover:underline">
        ← Вернуться в блог
      </Link>
    </div>
  );
}
