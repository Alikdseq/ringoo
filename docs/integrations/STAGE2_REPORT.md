# Этап 2 — HTTP-интеграция с 1С:УТ 11

**Дата:** 22 октября 2026  
**Статус:** подтверждённые методы реализованы на backend; живой API не вызывался.

## Расхождения этап 1 ↔ инструкция (исправлены)

| Тема | Было | Стало |
| --- | --- | --- |
| Env логина | `ONE_C_API_USER` | `ONE_C_LOGIN` (+ fallback) |
| Env пароля | `ONE_C_API_PASSWORD` | `ONE_C_PASSWORD` (+ fallback) |
| Таймаут | 15 с | 60 с (рекомендация инструкции) |
| Accept | не фиксирован | XML для GET, JSON для POST |
| Регистрация | не было | `POST SiteRegistration/registrate` + `onec_partner_id` |
| Папка «База» | не фильтровалась | исключается `00-00010097` |
| Заказы | не было | **по-прежнему не реализуем** (нет метода) |

## Реализованные HTTP-методы

1. `GET CatalogFolders/folders` → XML  
2. `GET CatalogProducts/products` → XML  
3. `POST SiteRegistration/registrate` → JSON  

Проверены **моками** в `tests/test_onec_http.py` и файловой выгрузкой.  
Реальный сервер 1С **не вызывался**.

## Изменённые / новые файлы

- `backend/integrations/onec/client.py` — Basic Auth, ошибки HTTP, XML/JSON  
- `backend/integrations/onec/parser.py` — строки XML, алиасы, исключение «База»  
- `backend/integrations/onec/importer.py` — `plan_from_parsed`, `fetch_and_plan_from_api`  
- `backend/integrations/onec/registration.py` — сервис партнёра  
- `backend/apps/users/models.py` + миграция `0005_user_onec_partner.py`  
- `backend/apps/products/management/commands/import_onec_catalog.py` — `--from-api`  
- `backend/config/settings/base.py` — env  
- `backend/tests/test_onec_http.py`, правки `test_onec_catalog.py`  
- `docs/integrations/1c-api-contract.md`, этот отчёт  

## Что нельзя делать до проверки на тестовой базе 1С

- Включать `ONE_C_API_ENABLED` против production.  
- Запускать `import_onec_catalog --apply` на рабочей БД сайта.  
- Автоповторять `SiteRegistration/registrate` после таймаута.  
- Отправлять заказы в 1С (метод не подтверждён).  
- Считать иллюстративные XML-теги инструкции единственной схемой без сверки живого ответа.

## Вопросы специалисту (заказы)

См. раздел 2 в `docs/integrations/1c-api-contract.md`.

## Безопасный запуск проверки

```bash
cd backend
python manage.py test tests.test_onec_catalog tests.test_onec_http

python manage.py import_onec_catalog \
  --folders ../integration1CandKassa/Иерархия\ Папок.xml \
  --products ../integration1CandKassa/Товары.xml
```

HTTP dry-run — только после явного разрешения, VPN/доступа и тестовых учёток.
