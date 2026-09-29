# Performance baseline — Ringoo

Документ для фиксации метрик до/после оптимизаций. Обновляйте после каждого спринта.

## Как снимать замеры

| Инструмент | URL / команда |
|------------|----------------|
| PageSpeed Insights | https://pagespeed.web.dev/ → `https://ringoo.ru` |
| Lighthouse (mobile, Slow 4G) | Chrome DevTools → Lighthouse |
| Bundle analyze | `cd frontend && cross-env ANALYZE=true npm run build -- --webpack` |
| API p95 | Sentry Performance / Django Silk на staging |

**Важно:** на ngrok/local (`RINGOO_NGROK_DEMO=1`, `NODE_ENV=development`) Next Image `unoptimized` — LCP на демо **не сравнивать** с продакшеном.

## Целевые KPI

| Метрика | Baseline (2026-05-21) | Цель P0 | Цель P1 |
|---------|----------------------|---------|---------|
| Lighthouse Performance (mobile) | замерить на ringoo.ru | ≥ 85 | ≥ 92 |
| LCP | замерить | < 2.5 s | < 1.8 s |
| INP | замерить | < 200 ms | < 100 ms |
| CLS | замерить | < 0.1 | < 0.05 |
| TTFB HTML | замерить | < 600 ms | < 400 ms |
| API GET /products/ p95 | — | < 300 ms | < 150 ms |

## Страницы для замера

- `/` — главная (LCP: hero / PromoFomo / первый товар)
- `/catalog` — каталог без фильтров
- `/catalog/category/iphone` — категория (или актуальный slug)
- `/products/{top-sku}` — PDP

## Bundle budgets (после `npm run build -- --webpack` с ANALYZE=true)

| Chunk | Budget (gzip) | Факт (2026-05-21) |
|-------|---------------|-------------------|
| First Load JS shared | < 180 KB | Turbopack build OK; analyzer требует `--webpack` |
| /catalog route | < 250 KB | см. отчёт после webpack analyze |

## Changelog

| Дата | Спринт | Изменения | LCP / Perf / INP |
|------|--------|-----------|------------------|
| 2026-05-16 | P0 | SSR home/catalog, Swiper off PLP (задумано) | замерить на prod |
| 2026-05-21 | Mobile opt | `galleryMode=false` в каталоге; defer Ringik; touch 44px; Modal sheet; `md:grid-cols-3`; reduced motion; dynamic below-fold home; удалены Hero3D/HeroSection | **замерить на ringoo.ru после деплоя** |

## Реализованные меры (код)

- Каталог: без Swiper на карточках (`galleryMode={false}`)
- Ringik: idle defer, скрыт на checkout
- Touch: `TOUCH_TARGET_MOBILE_CLASS`, CartItem, Input, filters, checkout chips
- Forms: `inputMode="tel"` / `numeric`
- Modal: mobile bottom sheet + close 44px
- PDP: Ringik скрыт на `< lg`; LCP `priority` на первом слайде галереи
- CI: `.github/workflows/lighthouse-ci.yml` (warn ≥ 85 Performance)
