import type { UiMode } from '@/lib/ui-mode/types';

/** Короткие строки для кнопок и подсказок (без дублирования API). */
export function addToCartButtonLabel(mode: UiMode, outOfStock: boolean): string {
  if (outOfStock) return 'Нет в наличии';
  return mode === 'svoi' ? 'Забрать как брат' : 'В корзину';
}

export function addToCartAriaLabel(mode: UiMode): string {
  return mode === 'svoi' ? 'Забрать товар (как брат)' : 'Добавить в корзину';
}

export function heroTitle(mode: UiMode): string {
  return mode === 'svoi' ? 'Своим — лучшая техника' : 'Электроника с доставкой';
}

export function heroSubtitle(mode: UiMode): string {
  return mode === 'svoi'
    ? 'Заходи в гости в каталог — всё как для своих.'
    : 'Каталог и акции — всё в одном месте';
}

export function heroCtaLabel(mode: UiMode): string {
  return mode === 'svoi' ? 'За покупками' : 'В каталог';
}

export function benefitsHeading(mode: UiMode): string {
  return mode === 'svoi' ? 'Почему к нам ходят свои' : 'Преимущества';
}

export function benefitsLead(mode: UiMode): string {
  return mode === 'svoi'
    ? 'Без лишней суеты — честно скажем, что к чему.'
    : 'Спокойно покупай — мы отвечаем за качество.';
}

export type BenefitCopy = { id: string; title: string; subtitle: string };

export function benefitsItems(mode: UiMode): BenefitCopy[] {
  if (mode === 'svoi') {
    return [
      {
        id: 'delivery',
        title: 'Доставка бесплатно от 100 ₽',
        subtitle: 'Привезём куда удобно — домой или на работу.',
      },
      {
        id: 'warranty',
        title: 'Гарантия 2 года',
        subtitle: 'Как положено — не отмахнёмся.',
      },
      {
        id: 'official',
        title: 'Техника «белая»',
        subtitle: 'Не с серой полки — всё прозрачно.',
      },
      {
        id: 'service',
        title: 'Сервис рядом',
        subtitle: 'Поможем и починим — без нервов.',
      },
    ];
  }
  return [
    {
      id: 'delivery',
      title: 'Бесплатная доставка от 100 ₽',
      subtitle: 'Привезём куда удобно — домой или на работу.',
    },
    {
      id: 'warranty',
      title: 'Гарантия 2 года',
      subtitle: 'Официальная гарантия на технику.',
    },
    {
      id: 'official',
      title: 'Официальная техника',
      subtitle: 'Сертифицированные поставки.',
    },
    {
      id: 'service',
      title: 'Сервисный центр',
      subtitle: 'Поможем с диагностикой и ремонтом.',
    },
  ];
}
