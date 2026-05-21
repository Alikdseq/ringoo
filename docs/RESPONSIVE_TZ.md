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
| Сетки товаров | 2 col (mobile), 2–3 (tablet), 3–4 (desktop) |
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
- Оболочка хедера: `HEADER_SHELL_CLASS` — те же горизонтальные отступы, `max-w-[1600px]` только для pill
- Компонент: [PageContainer.tsx](../frontend/src/components/layout/PageContainer.tsx)

**Запрещено на mobile:** `min-w-[...]` без `max-w-full`; дублирующие UiMode в хедере; подписи под иконками корзины/избранного `< md`.

## 5. Компоненты

| Компонент | Mobile | Desktop |
|-----------|--------|---------|
| Header | Лого + Каталог + иконки; бургер | Nav по центру |
| MobileMenu | Drawer, 44px | скрыт |
| Footer | 1 col → 2 → 4 | 4 col |
| CatalogContent | Drawer фильтров, grid 2 col | Sidebar + grid |
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
