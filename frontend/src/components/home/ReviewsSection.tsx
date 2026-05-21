'use client';

import { useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, MapPin, Star } from 'lucide-react';
import { TYPOGRAPHY, TYPOGRAPHY_MUTED } from '@/lib/theme/typography';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/theme/utils';

const REVIEW_TAGS = ['обработка', 'магазин', 'продукт', 'подарок', 'сервис'];

const MOCK_REVIEWS = [
  {
    id: '1',
    name: 'Имя Фамилия',
    date: '18 февраля',
    source: 'Яндекс',
    rating: 5,
    text: 'Всё понравилось, быстрая доставка, товар соответствует описанию. Рекомендую.',
  },
  {
    id: '2',
    name: 'Имя Фамилия',
    date: '15 февраля',
    source: 'Яндекс',
    rating: 4,
    text: 'Хороший магазин, менеджер помог с выбором. Небольшая задержка по срокам.',
  },
  {
    id: '3',
    name: 'Имя Фамилия',
    date: '10 февраля',
    source: 'Авито',
    rating: 5,
    text: 'Покупка в рассрочку оформили за пару минут. Телефон привезли в тот же день.',
  },
];

export function ReviewsSection() {
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [slideIndex, setSlideIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: 'left' | 'right') => {
    if (!scrollRef.current) return;
    const step = 320;
    scrollRef.current.scrollBy({
      left: dir === 'left' ? -step : step,
      behavior: 'smooth',
    });
    setSlideIndex(i => (dir === 'left' ? Math.max(0, i - 1) : i + 1));
  };

  return (
    <section className="border-t border-border bg-zinc-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className={TYPOGRAPHY.h2 + ' mb-6 text-center uppercase tracking-wide text-foreground'}>
          Отзывы
        </h2>

        {/* Рейтинг и счётчик */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-4 rounded-xl border border-border bg-white px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-semibold text-foreground">5.0</span>
            <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
            <span className="text-sm text-foreground-muted">| 298 отзывов</span>
          </div>
          <div className="flex gap-3 text-sm text-foreground-muted">
            <span>Авито 5.0</span>
            <span>Яндекс 5.0</span>
          </div>
        </div>

        {/* Теги-фильтры */}
        <div className="mb-6 flex flex-wrap justify-center gap-2">
          {REVIEW_TAGS.map(tag => (
            <button
              key={tag}
              type="button"
              onClick={() => setActiveTag(activeTag === tag ? null : tag)}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-medium transition-colors',
                activeTag === tag
                  ? 'bg-brand text-white'
                  : 'bg-white text-foreground-muted shadow-sm hover:bg-zinc-100'
              )}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Карусель отзывов */}
        <div className="relative">
          <button
            type="button"
            onClick={() => scroll('left')}
            className="absolute left-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-md transition-opacity hover:bg-white"
            aria-label="Назад"
          >
            <ChevronLeft className="h-6 w-6 text-foreground" />
          </button>
          <button
            type="button"
            onClick={() => scroll('right')}
            className="absolute right-0 top-1/2 z-10 -translate-y-1/2 rounded-full bg-white/90 p-2 shadow-md transition-opacity hover:bg-white"
            aria-label="Вперёд"
          >
            <ChevronRight className="h-6 w-6 text-foreground" />
          </button>

          <div
            ref={scrollRef}
            className="flex gap-4 overflow-x-auto scroll-smooth py-2 pb-4 [scrollbar-width:none] [-webkit-overflow-scrolling:touch] [&::-webkit-scrollbar]:hidden"
          >
            {MOCK_REVIEWS.map(r => (
              <article
                key={r.id}
                className="min-w-[280px] max-w-[320px] shrink-0 rounded-xl border border-border bg-white p-4 shadow-sm"
              >
                <div className="mb-2 flex items-center gap-1 text-danger">
                  <MapPin className="h-4 w-4" />
                </div>
                <p className={TYPOGRAPHY.bodySmall + ' font-medium text-foreground'}>{r.name}</p>
                <p className={TYPOGRAPHY_MUTED.bodySmall + ' mt-0.5'}>
                  {r.date} на{' '}
                  <a href="#" className="text-info underline">
                    {r.source}
                  </a>
                </p>
                <div className="mt-2 flex gap-0.5">
                  {[1, 2, 3, 4, 5].map(i => (
                    <Star
                      key={i}
                      className={cn(
                        'h-4 w-4',
                        i <= r.rating ? 'fill-amber-400 text-amber-400' : 'text-zinc-200'
                      )}
                    />
                  ))}
                </div>
                <p className={TYPOGRAPHY_MUTED.bodySmall + ' mt-2 line-clamp-3'}>{r.text}</p>
                <button
                  type="button"
                  className={TYPOGRAPHY_MUTED.bodySmall + ' mt-2 text-info hover:underline'}
                >
                  Читать дальше
                </button>
              </article>
            ))}
          </div>

          {/* Точки пагинации */}
          <div className="mt-4 flex justify-center gap-2">
            {MOCK_REVIEWS.map((_, i) => (
              <span
                key={i}
                className={cn(
                  'h-2 w-2 rounded-full transition-colors',
                  i === slideIndex ? 'bg-foreground' : 'bg-zinc-300'
                )}
                aria-hidden
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
