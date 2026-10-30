# Этап 1 интеграции с 1С — отчёт о выполнении

**Дата:** 22 октября 2026  
**Режим:** код добавлен; массовый apply в production **не** запускался; HTTP к 1С **не** вызывался.

---

## 1. Что изучено

- Django-приложения каталога, складов, заказов; Excel-импорт `bulk_import.py` (отдельный контур, не заменён).
- Модели `Category`, `Product`, `Store`, `Stock`, `Order`.
- Выгрузки `integration1CandKassa/Иерархия Папок.xml` и `Товары.xml`.
- Адреса специалиста: `CatalogFolders/folders`, `CatalogProducts/products` (метод/формат ответа не подтверждены).

Подтверждено повторным dry-run полной выгрузки:

| Показатель | Значение |
| --- | --- |
| Папок | 252 |
| Строк товаров | 7679 |
| Уникальных кодов | 3849 |

---

## 2. Созданные и изменённые файлы

### Создано

- `backend/integrations/onec/__init__.py`
- `backend/integrations/onec/parser.py`
- `backend/integrations/onec/importer.py`
- `backend/integrations/onec/client.py`
- `backend/integrations/onec/fixtures/sample_folders.xml`
- `backend/integrations/onec/fixtures/sample_products.xml`
- `backend/apps/products/management/commands/import_onec_catalog.py`
- `backend/apps/products/migrations/0006_category_product_onec_codes.py`
- `backend/apps/stores/migrations/0005_store_onec_warehouse_flags.py`
- `backend/tests/test_onec_catalog.py`
- `docs/integrations/1c-api-contract.md`
- `docs/integrations/STAGE1_REPORT.md`
- `docs/integrations/onec_import_report_dry_run.json` (после команды)

### Изменено

- `backend/apps/products/models.py` — `Category.onec_code`, `Product.onec_code`, `Product.onec_type`
- `backend/apps/stores/models.py` — `onec_warehouse_id`, `onec_warehouse_name`, `is_warehouse`
- `backend/config/settings/base.py` — `ONE_C_API_*`

---

## 3. Что реально реализовано

1. **Парсер XML** папок и товарных строк.
2. **Dry-run план** с JSON-отчётом: create/update/skip/ambiguous, склады, серии, битые папки, пустые цены/остатки.
3. **Apply** за флагами `--apply --i-understand-apply` (не запускался на боевых данных в этом этапе).
4. **HTTP-клиент** с `ONE_C_API_ENABLED=false` по умолчанию; без секретов в коде.
5. **Контракт** для специалиста 1С с разделением известных и предлагаемых путей.
6. **Тесты** парсера, dry-run, клиента, сопоставления по `onec_code`.

Правила:

- один `code` → одна карточка;
- пустой `quantity` ≠ 0;
- битая папка → товар не создаётся в плане create;
- серии только в замечаниях, без размножения карточек;
- существующие slug при update не меняются.

---

## 4. Как запустить dry-run

Из каталога `backend` (после `migrate` на вашей БД):

```bash
python manage.py import_onec_catalog ^
  --folders "..\integration1CandKassa\Иерархия Папок.xml" ^
  --products "..\integration1CandKassa\Товары.xml" ^
  --report "..\docs\integrations\onec_import_report_dry_run.json"
```

Запись в БД (только после проверки отчёта):

```bash
python manage.py import_onec_catalog ... --apply --i-understand-apply
```

Переменные HTTP (пока не включать без доступа):

- `ONE_C_API_BASE_URL=http://localhost/ut11_test/hs`
- `ONE_C_API_ENABLED=true` — только после согласования
- `ONE_C_API_USER` / `ONE_C_API_PASSWORD`

---

## 5. Пример результата dry-run

На пустой БД (нет существующих `onec_code`) по полной выгрузке:

| Метрика | Значение |
| --- | --- |
| Папок create | 252 |
| Товаров create | 3836 |
| Товаров skip | 13 |
| Остатков upsert | 6316 |
| Остатков skip (нет склада/кол-ва) | 1363 |
| Складов | 11 |
| Строк с серией (замечание) | 858 |
| Без цены | 12 |
| Без папки в дереве | 1 (`Акционный товар` / `00-00010097`) |

Краткая сводка с примерами: `docs/integrations/onec_import_report_dry_run.json`.  
Полный построчный JSON получается той же командой `--report` (несколько МБ).

---

## 6. Тесты

Команда:

```bash
set DJANGO_SETTINGS_MODULE=config.settings.test
python -m pytest tests/test_onec_catalog.py -q --no-cov
```

**Результат:** 10 passed.

---

## 7. Что пока не подключено и почему

| Тема | Почему |
| --- | --- |
| Живой HTTP к `folders` / `products` | Нет подтверждённого метода, формата ответа и доступа из окружения сайта |
| Передача заказов / статусов | Нет контракта методов |
| Сбер / касса | Вне этапа 1 |
| Apply на production | Нужна проверка dry-run человеком и бэкап |
| Учёт серий как отдельных единиц продажи | Нет бизнес-правила от 1С |

---

## 8. Вопросы специалисту 1С

См. полный список в `docs/integrations/1c-api-contract.md` §5. Критично:

1. GET или POST на известные пути и пример ответа.  
2. Как сайт достучится до сервиса (не только localhost).  
3. `code` — уникальный ключ номенклатуры?  
4. Серии и заказы с сайта.  
5. Папка `00-00010097` для «Акционный товар».

---

## 9. Безопасный следующий шаг

1. Специалист 1С присылает пример HTTP-ответа `folders` и `products`.  
2. Сайт включает клиент только на тестовом контуре (`ONE_C_API_ENABLED`).  
3. Сверка dry-run HTTP vs XML.  
4. Apply на **копии** БД, проверка каталога/корзины/URL.  
5. Только затем — осторожный apply на staging/production с бэкапом.
