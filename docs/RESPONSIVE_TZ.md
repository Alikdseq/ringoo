# ТЗ: адаптивность Ringoo (mobile-first)

**Версия:** 1.0  
**Дата:** 2026-05-20  
**Связанные документы:** [DESIGN_SPEC.md](./DESIGN_SPEC.md) §9, [UX.md](./UX.md), [RESPONSIVE_QA_CHECKLIST.md](./RESPONSIVE_QA_CHECKLIST.md)

---

## 1. Цель

Обеспечить качественное отображение витрины и ERP на экранах **от 320px** до desktop без горизонтального скролла страницы, с удобными touch-зонами и едиными отступами.

## 2. Критерии приёмки

| Критерий | Требование |
|----------|------------|
| Минимальная ширина | 320px, без overflow-x на `body` |
| Touch | ≥ 44×44px на `< lg` для кликабельных элементов |
| Типографика | H1 масштабируется; body ≥ 16px на mobile |
| Сетки товаров | **1 col** (mobile &lt; md), 2 col (md), 3 col (lg) — `PRODUCT_CARD_GRID_CLASS` |
| Режимы UI | official / svoi — читаемо на 320–390px |
| Admin | drawer-меню `< lg`, таблицы в `overflow-x-auto` |

## 3. Матрица устройств

| Viewport | Tailwind | Примеры |
|----------|----------|---------|
| 320px | default | iPhone SE |
| 360–390px | default | Android, iPhone 14 |
| 414px+ | sm (640) | Plus-модели |
| 768px | md | iPad portrait |
| 1024px | lg | iPad landscape, sidebar каталога |
| 1280px+ | xl | Desktop |

## 4. Layout-правила (источник истины)

- Контейнер витрины: `CONTAINER_CLASS` = `mx-auto max-w-6xl px-4 sm:px-6 lg:px-8` — [spacing.ts](../frontend/src/lib/theme/spacing.ts)
- Широкий контейнер (каталог, акции): `CONTAINER_WIDE_CLASS` = `max-w-7xl` + те же padding
- Оболочка хедера: `HEADER_OUTER_CLASS` — те же горизонтальные отступы, `max-w-[1600px]` только для pill
- Сетка карточек товара: `PRODUCT_CARD_GRID_CLASS` в [spacing.ts](../frontend/src/lib/theme/spacing.ts)
- Компонент: [PageContainer.tsx](../frontend/src/components/layout/PageContainer.tsx)

**Запрещено на mobile:** `min-w-[...]` без `max-w-full`; **два** `BrandLogo` в хедере; `UiModeToggle` compact в шапке (только в `MobileMenu`); подписи под иконками поиска/корзины `< md`; стрелки Swiper на карточках (только свайп + dots).

**Корень страницы:** `html, body` — `overflow-x: hidden`, `overscroll-behavior-x: none` ([globals.css](../frontend/src/app/globals.css)).

**Flat-секции главной:** `HOME_SECTION_CLASS` ([spacing.ts](../frontend/src/lib/theme/spacing.ts)); откат — `NEXT_PUBLIC_MOBILE_FLAT_SECTIONS=0`. См. [MOBILE_VITRINE_TZ.md](./MOBILE_VITRINE_TZ.md).

## 5. Компоненты

| Компонент | Mobile | Desktop |
|-----------|--------|---------|
| Header | **Один** крупный лого + «Каталог» (текст) + иконки 48px; бургер | Nav + UiMode в шапке |
| MobileMenu | Drawer, 44px | скрыт |
| Footer | 1 col → 2 → 4 | 4 col |
| CatalogContent | Drawer фильтров, grid **1 col** | Sidebar + grid 2–3 col |
| ProductPageClient | Stack, H1 `text-2xl` | 2 col |
| AdminLayout | Off-canvas sidebar | Fixed sidebar 256px |

## 6. Инвентарь страниц (51 route)

### Приоритет 1 — витрина

- `/` — главная, hero, секции
- `/catalog`, `/catalog/category/[slug]`
- `/products/[slug]`
- `/cart`, `/checkout`
- `/stores`, `/stores/[slug]`
- `/about`, `/staff/[slug]`
- `/promotions`
- `/profile`, `/orders`, `/orders/[id]`
- `/login`, `/register`

### Приоритет 2

- `/blog`, `/news`, `/wishlist`, `/installment`, `/order-status`, `/site-map`, `/docs/*`

### Приоритет 3 — admin

- `/admin/*` — все ERP-страницы

## 7. Нефункциональные требования

- Lighthouse Performance ≥ 85 — без тяжёлого JS ради адаптива
- `prefers-reduced-motion` — упрощение parallax/3D
- Не менять API auth/cart/orders без необходимости

## 8. Реализация (фазы)

См. план в `.cursor/plans/` и чеклист [RESPONSIVE_QA_CHECKLIST.md](./RESPONSIVE_QA_CHECKLIST.md).
