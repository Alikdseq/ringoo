# ТЗ: витрина Ringoo — хедер, стабильность, цвета, модели, mobile layout

**Версия:** 1.0  
**Дата:** 2026-05-21  
**Связанные документы:** [RESPONSIVE_TZ.md](./RESPONSIVE_TZ.md), [RESPONSIVE_QA_CHECKLIST.md](./RESPONSIVE_QA_CHECKLIST.md), [API.md](./API.md)

## Задачи и критерии приёмки

| # | Задача | Критерий |
|---|--------|----------|
| 1 | Логотип крупнее | mobile 48×104px, desktop 80×148px |
| 2 | «Каталог» с текстом на mobile | иконка + подпись на всех ширинах |
| 3 | Кнопки хедера крупнее | touch ≥ 48px до md, иконки 24px |
| 4 | Страница не сдвигается вбок | `overflow-x: hidden` + `overscroll-behavior-x: none` на корне |
| 5 | Цвет ↔ фото | синхронизация hex; аудит `audit_color_consistency` |
| 6 | Фильтр «Модель» | `GET products/product-models/` + `?model=` в списке товаров |
| 7 | Mobile «распаковка» | `HOME_SECTION_*`, флаг `NEXT_PUBLIC_MOBILE_FLAT_SECTIONS=0` для отката |

## Токены layout

- `HEADER_ICON_BUTTON_CLASS` — 48px до md
- `HOME_SECTION_CLASS` / `HOME_SECTION_INNER_CLASS` — секции главной
- `PRODUCT_CARD_GRID_CLASS` — 1 / 2 / 3 колонки

## Команды

```bash
docker compose exec web python manage.py fix_color_hex_from_hints
docker compose exec web python manage.py audit_color_consistency --limit 30
```

## Откат flat-секций

В `frontend/.env.local`:

```
NEXT_PUBLIC_MOBILE_FLAT_SECTIONS=0
```
