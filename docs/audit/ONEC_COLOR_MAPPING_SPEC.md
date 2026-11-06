# Спецификация: цветовые варианты ↔ 1С (обновлено)

**Статус:** PARTIAL implementation + NEEDS BUSINESS DECISION по источнику GUID характеристики в XML.

## Фактическая модель сайта

### ProductColor (внутренний ID варианта)

Стабильный UUID `ProductColor.id` — основной внутренний ключ витрины/корзины/заказа.

Добавлены поля:

| Поле | Назначение |
|---|---|
| `sku` | Артикул варианта |
| `barcode` | Штрихкод |
| `onec_code` | Код номенклатуры 1С **для этого варианта** (если в 1С отдельный code на цвет) |
| `onec_characteristic_ref` | GUID/ссылка характеристики 1С (если появится в выгрузке) |
| `mapping_status` | `unmatched` / `matched` / `ambiguous` / `conflict` / `inactive` |

Название цвета (`label`) — **только отображение**, не ключ сопоставления.

### OrderItem

Сохраняет `color` FK + снимки label/slug/hex + `onec_product_code` / `onec_series_id`.  
Исторические заказы не переписываются.

### Склад

`Stock` уникален по `(product, store, onec_series_id)`.  
**seriesId ≠ цвет.** Серия — серийный учёт (IMEI/SN), не палитра.

## Payload заказа в 1С

`build_order_items_payload`:

1. Если у цвета `mapping_status=matched` и заполнен `onec_code` → `productCode` = код варианта.
2. Иначе — прежняя логика (`OrderItem.onec_product_code` / `Product.onec_code`).
3. Дополнительно (информативно): `colorLabel`, `colorSlug`, `colorId`, опционально `characteristicRef`.
4. `seriesId` без изменений.

## Импорт XML

Текущий парсер: `code`, `sklad`, `series`, `seriesID` — **без поля color**.  
Нельзя угадывать цвет по `name`.  
Dry-run/apply сохранены; неоднозначный цвет не создаётся автоматически из названия.

## Админ-сопоставление

`GET/PATCH /api/v1/admin/products/color-mappings/`  
Конфликт одинакового `onec_code` у двух цветов → `conflict`.

## Приоритет ключей

1. `onec_characteristic_ref` (если реально есть в данных 1С)  
2. `onec_code` варианта (подтверждённый)  
3. `sku` / `barcode`  
4. Ручной matched в админке  

## Ограничения

- Без отдельного code/GUID на цвет в 1С однозначный обмен **невозможен** — только UX-цвет + общий productCode (**вариант B**), либо владелец заводит отдельные номенклатуры (**вариант A**).
- Нужны примеры production XML с характеристиками — **NEEDS BUSINESS DECISION / данные 1С**.
