# Главная страница: официальный и свойский режим

Переключатель: `UiModeToggle`, контекст `useUiMode()`, стили: `html[data-ui-mode]` + классы `body.mode-official` / `body.mode-svoi`.

Тексты блоков главной (кроме уже вынесенных в `lib/ui-mode/copy.ts` для героя/корзины) лежат в **`src/locales/home-page.json`** → хук **`useHomePageCopy()`** (`src/lib/locales/useHomePageCopy.ts`).

## Блоки по порядку в `page.tsx` (сопоставление с ТЗ)

| Порядок на странице | Компонент | ТЗ (блок) | Что меняется в svoi |
|---------------------|-----------|-----------|---------------------|
| 1 | `PromoFomoCarousel` | Акции (2) | Заголовок секции + `slideEyebrow`; карусель/таймеры/«Забрать скидку» — те же |
| 2 | `HeroWithCategories` | Херо + быстрый каталог (1 + 3) | 3D как был; вместо категорий из API — `QuickCatalogSvoi*` из JSON; херо по Figma — см. ниже |
| 3 | `TodaysProductsCarousel` | Товары дня (4) | Только заголовок/подзаголовок/`seeAll` из JSON |
| 4 | `InstallmentZeroSection` | Рассрочка (5) | Тексты формы и кнопок; формула рассрочки без изменений |
| 5 | `NearbyStoresSection` | Магазины (6) | Заголовок, подзаголовок, подписи кнопок/«Маршрут»; API и карта те же |
| 6+ | `PopularNowSection`, `VideoReviewsSection`, … | Остальное (7) | Пока идентично официальному |

## Блок 1 (херо, Figma)

В коде оставлен комментарий в `HeroWithCategories`: финальный слой (видео / Зина и Бола) подключается по макету из Figma поверх текущей сетки.

## Быстрый каталог (свойский) — URL

Пути заданы в `home-page.json` → `svoi.quickCatalog`. При смене категорий на бэкенде проверить `slug` в `/catalog?category=…` и при необходимости обновить JSON.

## Чек-лист

- [ ] Режим сохраняется (`ringoo_ui_mode` localStorage + cookie).
- [ ] На `body` есть `mode-official` / `mode-svoi`.
- [ ] После правок текстов — править только `home-page.json` (или дублировать ключи в `official` / `svoi`).
