# RINGOO — Pre-Deployment Audit Report

**Дата:** 07.11.2026
**Репозиторий:** `C:\ringoo`
**Ветка:** `main` (ahead of origin/main на 6 commits + большой uncommitted working tree)
**Commit / push / deploy:** не выполнялись
**Живые POST в 1С / реальные платежи / импорт в рабочую БД:** не выполнялись

> Запрошенный файл `docs/audit/RINGOO_FULL_AUDIT.md` **отсутствует**; использован фактический `docs/audit/RINGO_FULL_AUDIT.md`.

---

## 1. Общий результат аудита

Проект технически близок к безопасному переносу на AdminVPS **как staging/production-заготовка**, но **не готов** к полноценному запуску магазина с рабочей 1С и боевыми платёжными ключами.

Исправлены подтверждённые HIGH/MEDIUM дефекты в рамках сессии (см. §16). Остаются EXTERNAL-зависимости (владелец 1С, offsite S3, DNS/TLS/VPS) и незакоммиченный объём изменений.

---

## 2. Фактическая архитектура проекта

```
Next.js (frontend) → Django REST API (web/gunicorn prod) → PostgreSQL
                         ↑
              Redis ← Celery worker + Celery Beat
                         ↑
         ЮKassa (опц.) | 1С HTTP/XML (опц., импортёр → БД)
         backups (локально; S3 offsite опц.)
```

| Компонент | Факт в коде | Статус |
|-----------|-------------|--------|
| Витрина/админ читают PostgreSQL Ringoo | Да; публичный API без live 1С на page load | **PASS** |
| Dev compose | `runserver`, порты DB/Redis на хост | **PASS** (dev only) |
| Prod overlay | gunicorn, `node server.js`, DB/Redis ports reset, DEBUG=False | **PASS** |
| 1С catalog Beat | `ONE_C_CATALOG_SYNC_ENABLED` default off | **PASS** |
| ЮKassa | default off; webhook → re-fetch API | **PASS** (mock) |
| Sber | default off | **PASS** |

---

## 3. Git status и изменённые файлы

**Статус:** dirty working tree (десятки modified + untracked).
**Не коммитить / не деплоить без ревью:** `copy-site/`, `integration1CandKassa/`, бинарные `.docx`, `промпт.txt`, локальные drill-скрипты.

Ключевые untracked по 1С/hardening (уже в дереве):

- `backend/apps/products/onec_protection.py`, `sync_models.py`, `migrations/0008_*`, `tasks.py`
- `backend/integrations/onec/catalog_sync.py`
- `backend/apps/admin_api/views/onec_sync.py`
- `frontend/src/app/admin/sync/`, `color-mappings/`
- `docs/audit/RINGOO_ONEC_FINAL_HARDENING_REPORT.md`, `RINGOO_STOCK_RESERVE_OPTIONS.md`

В этой сессии дополнительно изменены (см. §16).

---

## 4. Проверка backend

| Проверка | Статус | Доказательство |
|----------|--------|----------------|
| `manage.py check` (test) | **PASS** | 0 issues |
| `manage.py check` (production, с валидным env + mkdir logs) | **PASS** | после фикса `production.py` |
| Fail-closed production (DEBUG, SECRET_KEY, non-postgres role, strong DB password) | **PASS** | ImproperlyConfigured без секретов |
| Миграции applied (local docker) | **PASS** | products…0008, orders…0010, payments…0003, stores…0007 |
| `migrate --plan` | **PASS** | No planned operations |
| `makemigrations --check` | **FAIL** | Index rename drift по apps + `AlterField` ProductImage.upload_to (не применять вслепую) |
| ЮKassa unit/mock | **PASS** | `test_yookassa_payments`, `test_sec007_*`, `test_payment_security` |
| 1С protection / SyncLog / partner | **PASS** | `test_onec_*` |
| bank_transfer blocked | **PASS** | новый тест |
| Live 1С / live YK | **NOT TESTED** / **EXTERNAL** | запрещено правилами |

---

## 5. Проверка frontend

| Проверка | Статус | Доказательство |
|----------|--------|----------------|
| `tsc --noEmit` | **PASS** | exit 0 (Docker frontend) |
| vitest `src/lib/api/services` | **PASS** | 5 passed |
| vitest checkout page | **FAIL** | `React.act is not a function` в `checkout/page.test.tsx` (окружение RTL/React) |
| `next build` (ранее в hardening) | **PASS** | exit 0 |
| Admin sync / color-mappings / 1С RO UX | **PASS** (код) | страницы и nav; E2E браузер **NOT TESTED** |
| Checkout: bank_transfer скрыт | **PASS** | UI; API теперь тоже режет |
| Online pay UI flag | **PASS** | `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` default 0 |
| Returns/XLSX/backup/promocodes UI | **PASS** | флаги default off |

Адаптивность 360–1440: **NOT TESTED** (нет browser E2E в этом прогоне).

---

## 6. Проверка Docker

| Проверка | Статус | Доказательство |
|----------|--------|----------------|
| `compose … prod config` без env | **FAIL** | требует `CSRF_TRUSTED_ORIGINS` и др. — ожидаемо |
| `compose … prod config` с placeholder env | **PASS** | exit 0 |
| Prod: DB/Redis ports `!reset []` | **PASS** | `docker-compose.prod.yml` |
| Backend bind `127.0.0.1:8000` | **PASS** | не 0.0.0.0 наружу по умолчанию |
| Frontend prod command | **PASS** | `node server.js` |
| Backend prod command | **PASS** | gunicorn |
| `ONE_C_CATALOG_SYNC_*` в prod env | **PASS** | добавлено в overlay + `.env.production.example` |
| Полная пересборка prod-образов в этом прогоне | **NOT TESTED** | не запускалась (долго/не требуется для static audit); local stack уже поднят |

---

## 7. Проверка миграций

| Проверка | Статус |
|----------|--------|
| `0008_onec_catalog_synclog` graph / модель | **PASS** |
| Destructive ops в 0008 | **PASS** (create only) |
| Drift `makemigrations --check` | **FAIL** / **MEDIUM** — массовые RenameIndex + AlterField image; **не создавать** слепые миграции на VPS |
| Brand index restored in model Meta | **PASS** (исправлено; имя = 0005) |
| ProductColor index name pinned | **PASS** (исправлено) |

---

## 8. Проверка безопасности

| Тема | Статус | Комментарий |
|------|--------|-------------|
| JWT / cookies / blacklist | **PASS** (код + prior SEC tests) | |
| IDOR заказов (свой queryset) | **PASS** | `test_sec001_*`, filter `user=` |
| Guest access token | **PASS** | prior SEC-006 |
| Admin API staff + groups | **PASS** | |
| Webhook YK AllowAny | **PASS** trust (GET re-fetch) / **MEDIUM** residual DoS без IP allowlist | |
| Mass-assignment цены | **PASS** | сервер пересчитывает; client amount ignored |
| `bank_transfer` API | **PASS** после фикса | ранее **FAIL** |
| 1С sync / backups не для анонимов | **PASS** | admin permissions |
| Secrets in git | **PASS** (spot) | `.env` в gitignore; examples без реальных ключей |
| DEBUG production | **PASS** | запрещён |
| Axes / OTP / throttles | **PASS** | |
| Upload MIME | **NOT TESTED** глубоко | image pipeline существует |

---

## 9. Проверка платежей

| Тема | Статус |
|------|--------|
| Create: amount/order/idempotence | **PASS** |
| Webhook ≠ paid без API GET | **PASS** |
| Replay / one paid per order | **PASS** |
| Expire unpaid + reserve release | **PASS** (mock tests) |
| Repay after failed | **PASS** with MEDIUM ops caveat (multiple YK URLs) |
| Sber accidental enable | **PASS** (off) |
| Live sandbox charge | **NOT TESTED** / **EXTERNAL** |

---

## 10. Проверка корзины и заказов

| Тема | Статус |
|------|--------|
| Цена с сервера (FUNC-003) | **PASS** |
| Резерв при create в store | **PASS** (код + stock tests) |
| Online: cart до оплаты | **PASS** |
| Non-online: clear cart | **PASS** |
| StoreSelector GPS / Haversine | **PASS** (код); browser GPS **NOT TESTED** |
| Checkout E2E UI | **BLOCKED** / **FAIL** vitest act |

---

## 11. Проверка остатков и резервов

| Тема | Статус |
|------|--------|
| quantity / reserved / available | **PASS** |
| Atomic reserve | **PASS** |
| Cancel releases stock | **PASS** (`test_sec003_*`) |
| 1С не получает остатки с сайта | **PASS** |
| Политика A/B/C с 1С | **EXTERNAL** | `RINGOO_STOCK_RESERVE_OPTIONS.md` |
| Изменение бизнес-логики резервов | не выполнялось | |

---

## 12. Проверка 1С

| Тема | Статус |
|------|--------|
| Dry-run без записи каталога | **PASS** |
| SEO/images на update | **PASS** (`update_fields`) |
| Field protection PATCH/bulk/stock/admin | **PASS** |
| SyncLog | **PASS** |
| Parallel apply | **PASS** после cache lock (+ DummyCache fallback) | было **FAIL** |
| Beat default off | **PASS** |
| Color mappings UI | **PASS** (код) |
| Live import / registrate | **EXTERNAL** / **NOT TESTED** |

---

## 13. Проверка административной панели

| Тема | Статус |
|------|--------|
| Разделы sync / colors / catalog RO | **PASS** (код) |
| XLSX API disabled by flag | **PASS** |
| Returns/promocodes/backup nav hidden | **PASS** |
| Полный клик-аудит всех кнопок | **NOT TESTED** (нет browser automation в прогоне) |

---

## 14. Проверка резервного копирования

| Тема | Статус |
|------|--------|
| Локальный backup код + docs/ops | **PASS** (код существует) |
| Offsite S3 | **BLOCKED** / **EXTERNAL** — `BACKUP_OFFSITE_ENABLED` default 0; реальный бакет не подключался |
| Restore поверх prod | **запрещено** правилами; инструкция в `docs/ops/BACKUP_RESTORE_GUIDE.md` | **PASS** (док) / restore **NOT TESTED** |

**Вывод:** резервное копирование **не объявляется полностью готовым** без настроенного offsite и прогона restore на отдельной БД.

---

## 15. Проверка производительности

| Тема | Статус |
|------|--------|
| N+1 / prefetch | **NOT TESTED** (нет профилирования в прогоне) |
| Пагинация admin/stock | **PASS** (есть) |
| Индексы каталога | **PASS** с оговоркой drift имён |

---

## 16. Исправленные проблемы (эта сессия)

| ID | Severity | Проблема | Исправление | Тест |
|----|----------|----------|-------------|------|
| P1 | HIGH | Parallel catalog apply race | Redis `cache.add` lock + DummyCache detect | `test_apply_lock_rejects_second_holder` |
| P2 | HIGH/MED | `bank_transfer` принимался API | Reject в `OrderCreateSerializer.validate` | `test_payment_type_bank_transfer_disabled` |
| P3 | MEDIUM | Brand index «съеден» Meta → makemigrations RemoveIndex | Вернули `products_product_brand_idx` | makemigrations products без RemoveIndex |
| P4 | MEDIUM | ProductColor index rename noise | Явное `name=` как в 0003 | — |
| P5 | MEDIUM | Prod LOGGING FileHandler без `/app/logs` | `os.makedirs` перед LOGGING | `check` production OK |
| P6 | LOW/OPS | Нет явных ONE_C catalog / backup flags в prod examples | `.env*.example` + `docker-compose.prod.yml` | compose config |

---

## 17. Оставшиеся проблемы

| ID | Severity | Статус | Описание |
|----|----------|--------|----------|
| R1 | MEDIUM | **FAIL** | `makemigrations --check` dirty (RenameIndex multi-app, AlterField ProductImage) — не автофиксить на VPS |
| R2 | MEDIUM | **FAIL** | vitest checkout: `React.act is not a function` |
| R3 | MEDIUM | open | YK webhook без IP allowlist (mitigated by GET) |
| R4 | MEDIUM | open | Multiple YK payment URLs after failed repay |
| R5 | MEDIUM | open | Stuck SyncLog `running` до 120 мин |
| R6 | LOW | open | docs/DEPLOYMENT.md устаревшие пути `.env` vs root `.env.production` |
| R7 | EXTERNAL | — | Контракт 1С / GUID / registrate |
| R8 | EXTERNAL | — | Offsite S3 + restore drill |
| R9 | ops | — | Большой uncommitted tree + `copy-site/` |

---

## 18. Результаты тестов (фактический прогон)

| Набор | Результат |
|-------|-----------|
| `test_onec_sync_log` + bank_transfer + field_protection | **OK** |
| `test_yookassa_payments` + `test_sec007` + related (ранее 42) | **OK** |
| `test_sec001` + `test_payment_security` + `test_func003` + `cart.tests` | **68 OK** |
| production `check` (валидный env) | **OK** |
| frontend `tsc` | **OK** |
| vitest services | **OK** |
| vitest checkout page | **FAIL** (1) |
| Live E2E / PG concurrency suite | **NOT TESTED** в этом прогоне |
| `next build` | **PASS** (hardening session); полный rebuild prod images **NOT TESTED** сейчас |

---

## 19. Вопросы к владельцу 1С

1. Поведение `SiteRegistration/registrate` при повторном телефоне.
2. Формат ответа и стабильный GUID контрагента.
3. Метод поиска существующего контрагента.
4. Расписание/лимиты GET folders/products.
5. GUID характеристик/цветов в выгрузке.
6. Политика временно отсутствующих SKU.
7. Учёт интернет-резервов Ringoo на складе (вариант A/B/C).

---

## 20. Что необходимо сделать перед AdminVPS

1. Закоммитить только релизный diff (без `copy-site/`, без секретов).
2. Подготовить `.env.production` из `.env.production.example` (сильные пароли, `ringoo_app`, Redis password).
3. TLS + reverse proxy (Caddy/Nginx examples в `docs/ops`).
4. Firewall: не публиковать 5432/6379.
5. `migrate` только после бэкапа; **не** `makemigrations` на сервере.
6. `collectstatic`; volumes `media`/`logs`/`static`.
7. `ONE_C_*` и `YOOKASSA_*` оставить выкл. до smoke.
8. Настроить SMTP / MONITORING по ops-докам.
9. Прогон backup → restore на **отдельной** БД.
10. Rebuild frontend image с нужными `NEXT_PUBLIC_*`.

---

## 21. Что пока нельзя включать

- `ONE_C_API_ENABLED=1` без согласованного контура
- `ONE_C_CATALOG_SYNC_ENABLED=1` / Beat catalog
- `ONE_C_SYNC_PARTNER_ON_REGISTER=1` без ответа по registrate
- `ONE_C_ORDER_SYNC_ENABLED=1`
- Боевые ключи ЮKassa (`YOOKASSA_TEST_MODE=0`)
- `SBER_ECOM_ENABLED` / production Sber URL
- `BACKUP_OFFSITE_ENABLED` без бакета и ключей
- `RETURNS_ENABLED` / XLSX import / promocodes UI
- `docker compose down -v`, restore поверх prod, live apply 1С

---

## 22. Итоговая оценка готовности

| Направление | Оценка | Условия |
|-------------|--------|---------|
| 1. Сборка production-образов | **ГОТОВО ПОСЛЕ УСЛОВИЙ** | Чистый env template, review uncommitted files, успешный `compose … prod build` на целевой машине |
| 2. Перенос на AdminVPS | **ГОТОВО ПОСЛЕ УСЛОВИЙ** | TLS, firewall, `.env.production`, migrate после бэкапа, без включения 1С/live pay |
| 3. Production платёжные ключи | **НЕ ГОТОВО** | Нужны staging smoke на test keys, мониторинг webhook, политика late pay; live keys отдельно |
| 4. Рабочая 1С | **НЕ ГОТОВО** | Нет live приёмки контракта; Beat/apply держать выкл. |
| 5. Запуск магазина для покупателей | **НЕ ГОТОВО** | Каталог/остатки/1С, платежи, backups offsite, E2E и ops checklist не закрыты |

---

**Главный вывод:** код Ringoo можно готовить к **развёртыванию staging на AdminVPS** с выключенными 1С и онлайн-оплатой. Заявлять готовность интернет-магазина к покупателям или готовность рабочей 1С — нельзя.

### Примечание по поздним read-only субаудитам

Отчёты [YooKassa/checkout/reserves](73f80764-0f10-4dcb-a6b6-0cf064504a37) и [1C integration](0e6b0cd0-6225-4f4e-b01a-5d2a9d968527) снимали снимок **до** правок §16. Их пункты `bank_transfer` API gap и parallel apply race **закрыты** исправлениями P1/P2; актуальный статус — таблицы выше, не «FAIL» в тех субаудитах. Остальное из субаудитов (webhook IP MEDIUM, repay URL MEDIUM, stuck `running` 120 мин) по-прежнему в §17.
