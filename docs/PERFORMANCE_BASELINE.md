# Performance baseline — Ringoo

Документ для фиксации метрик до/после оптимизаций. Обновляйте после каждого спринта.

## Как снимать замеры

| Инструмент | URL / команда |
|------------|----------------|
| PageSpeed Insights | https://pagespeed.web.dev/ → `https://ringoo.ru` |
| Lighthouse (mobile, Slow 4G) | Chrome DevTools → Lighthouse |
| Bundle analyze | `cd frontend && npm run analyze` |
| API p95 | Sentry Performance / Django Silk на staging |

## Целевые KPI

| Метрика | Baseline (заполнить) | Цель P0 | Цель P1 |
|---------|----------------------|---------|---------|
| Lighthouse Performance (mobile) | — | ≥ 85 | ≥ 92 |
| LCP | — | < 2.5 s | < 1.8 s |
| INP | — | < 200 ms | < 100 ms |
| CLS | — | < 0.1 | < 0.05 |
| TTFB HTML | — | < 600 ms | < 400 ms |
| API GET /products/ p95 | — | < 300 ms | < 150 ms |

## Страницы для замера

- `/` — главная (LCP: hero `/fon/fon.jpg` или первый товар)
- `/catalog` — каталог без фильтров
- `/catalog/category/iphone` — категория
- `/products/{top-sku}` — PDP

## Bundle budgets (после `npm run analyze`)

| Chunk | Budget (gzip) | Факт (дата) |
|-------|---------------|-------------|
| First Load JS shared | < 180 KB | — |
| /catalog route | < 250 KB | — |

## Changelog

| Дата | Спринт | Изменения | LCP / Perf / INP |
|------|--------|-----------|------------------|
| 2026-05-16 | P0 | SSR home/catalog, Swiper off PLP, PDP API cache, bundle analyze, lazy maps | замерить на prod |
