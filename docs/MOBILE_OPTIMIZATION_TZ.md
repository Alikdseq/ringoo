# ТЗ: мобильная оптимизация Ringoo

**Версия:** 1.0  
**Дата:** 2026-05-21  
**Связанные документы:** [RESPONSIVE_TZ.md](./RESPONSIVE_TZ.md), [PERFORMANCE.md](./PERFORMANCE.md), [PERFORMANCE_BASELINE.md](./PERFORMANCE_BASELINE.md), [RESPONSIVE_QA_CHECKLIST.md](./RESPONSIVE_QA_CHECKLIST.md)

---

## 1. Цель и scope

Обеспечить витрину Ringoo с **mobile-first** UX, Core Web Vitals в зелёной зоне на продакшене и регрессионной проверкой интеграций перед деплоем.

| In scope | Out of scope |
|----------|--------------|
| `/`, `/catalog`, PDP, `/cart`, `/checkout`, auth, P2-страницы витрины | Полный редизайн admin ERP |
| Touch ≥ 44px, сетки, формы, модалки | Замена Яндекс.Карт |
| Performance (JS, images, defer) | CDN-инфраструктура (только рекомендации) |

**Не ломать:** API auth/cart/orders, режимы `official` / `svoi`, ключи TanStack Query ([AGENTS.md](../AGENTS.md)).

---

## 2. Матрица устройств

| Viewport | Tailwind | Каталог | Навигация |
|----------|----------|---------|-----------|
| 320–639 | default | 2 col | Бургер + иконки |
| 640–767 | `sm` | 2 col | Бургер |
| 768–1023 | `md` | **3 col** | Бургер до `lg` |
| 1024+ | `lg` | 3 col + sidebar | Полная nav |

---

## 3. Touch и типографика

- `< lg`: интерактивные элементы **≥ 44×44px** — токен `TOUCH_TARGET_MOBILE_CLASS` в [spacing.ts](../frontend/src/lib/theme/spacing.ts).
- Body ≥ 16px на mobile (`Input` — `text-base` до `sm`).
- `:active` / `focus-visible` на кнопках и chip.

---

## 4. Производительность

| Мера | Реализация |
|------|------------|
| Каталог без Swiper | `ProductCard` `galleryMode={false}` в [CatalogContent.tsx](../frontend/src/app/catalog/CatalogContent.tsx) |
| Ringik defer | [RingikLauncher.tsx](../frontend/src/components/ringik/RingikLauncher.tsx) — `requestIdleCallback`, скрыт на `/checkout` |
| Below-fold home | `dynamic()` — VideoReviews, GiftTiles, Benefits, Subscribe |
| LCP | `priority` на первом кадре PDP [ProductGallery.tsx](../frontend/src/components/features/products/ProductGallery.tsx) |
| Reduced motion | [usePrefersReducedMotion.ts](../frontend/src/lib/hooks/usePrefersReducedMotion.ts) |

**Ngrok/dev:** `images.unoptimized` — метрики PSI на демо **не сравнивать** с [ringoo.ru](https://ringoo.ru).

---

## 5. Формы

- Телефон: `type="tel"` + `inputMode="tel"` + `autoComplete="tel"` — login, register, checkout, order-status.
- Цена в фильтрах: `inputMode="numeric"`.

---

## 6. Модалки

- [Modal.tsx](../frontend/src/components/ui/Modal.tsx): bottom sheet на mobile, `max-h-[90dvh]`, close 44px, Escape, scroll lock.

---

## 7. KPI приёмки

| Метрика | P0 | P1 |
|---------|-----|-----|
| Lighthouse Performance (mobile, ringoo.ru) | ≥ 85 | ≥ 92 |
| LCP | < 2.5 s | < 1.8 s |
| CLS | < 0.1 | < 0.05 |
| INP | < 200 ms | < 100 ms |
| Touch | ≥ 44px на `< lg` | — |
| Horizontal scroll body | нет на 320–1280px | — |

---

## 8. Приёмка

1. [RESPONSIVE_QA_CHECKLIST.md](./RESPONSIVE_QA_CHECKLIST.md) — P0 на 320/375/768/1024.
2. Регрессия ngrok: login → cart → checkout (guest/auth).
3. [PERFORMANCE_BASELINE.md](./PERFORMANCE_BASELINE.md) — замер до/после на prod.

---

## 9. CI

Workflow [.github/workflows/lighthouse-ci.yml](../.github/workflows/lighthouse-ci.yml) — Lighthouse на prod URL (manual + schedule).
