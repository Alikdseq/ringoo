import Image from 'next/image';
import Link from 'next/link';
import { cn } from '@/lib/theme/utils';

const LOGO_SRC = '/logo/logonb.png';

interface BrandLogoProps {
  /** Если false — только картинка (для обёртки во внешний Link). */
  link?: boolean;
  href?: string;
  className?: string;
  height?: number;
  /** Ширина контейнера; по умолчанию ~3.8× height. В хедере задайте меньше, чтобы «Каталог» был у знака. */
  width?: number;
  priority?: boolean;
  onClick?: () => void;
}

export function BrandLogo({
  link = true,
  href = '/',
  className,
  height = 36,
  width: widthProp,
  priority = false,
  onClick,
}: BrandLogoProps) {
  const width = widthProp ?? Math.round(height * 3.8);

  const image = (
    <span
      className="relative inline-block shrink-0"
      style={{ width, height }}
    >
      <Image
        src={LOGO_SRC}
        alt={link ? '' : 'Ringoo'}
        fill
        className="object-contain object-left"
        sizes={`${width}px`}
        priority={priority}
        aria-hidden={link || undefined}
      />
    </span>
  );

  if (!link) {
    return <span className={cn('inline-flex shrink-0 items-center', className)}>{image}</span>;
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn('inline-flex shrink-0 items-center', className)}
      aria-label="Ringoo — на главную"
    >
      {image}
    </Link>
  );
}
