# Производительность Admin API (N+1 и отчёты)

## Отчёты `admin/reports/*`

`RevenueReportView`, `OrdersReportView`, `TopProductsReportView` строят ответы через **агрегаты** Django ORM (`values`, `annotate`, `Sum`, `Count`) без итерации по полным объектам заказов в Python — типичного N+1 при просмотре списка там нет.

## Списки, где уже есть оптимизации

- **Товары админки** (`ProductAdminListView`): `select_related("category")`, `prefetch_related("stock_items")` — поле `available_quantity_total` в сериализаторе обходит связанные `Stock` без отдельного запроса на каждую строку.
- **Отзывы** (`ReviewAdminListView`): `select_related("product", "user")`.
- **Публичный контент** (`ArticleViewSet`, `NewsViewSet`): `select_related` / `prefetch_related` в `get_queryset`.

## Рекомендация при новых list-эндпоинтах

1. Включить **django-debug-toolbar** (только dev) или **django-silk** и прогнать тяжёлые сценарии.
2. Для списков с вложенными объектами в сериализаторе — явно **`select_related` / `prefetch_related`** на `get_queryset`.
3. Экспорт в CSV (`OrderAdminExportView`): если объём вырос, рассмотреть **iterator()** и ограничение периода по умолчанию.
