# BLOCK 4 — FINAL CLOSURE REPORT

**Дата:** 2026-11-06  
**Репозиторий:** `C:\ringoo`  
**HEAD на старте этапа:** `1f835938bc28b1f8459a83b10b082b41998fbc29`  
**Push:** не выполнялся  
**Production migrate / deploy / write в 1С / боевые платежи:** не выполнялись

---

## 1. Общий результат

**Статус блока №4: COMPLETED WITH EXTERNAL DEPENDENCIES**

| Направление | Статус |
|---|---|
| Offsite S3-compatible pipeline (код + MinIO drill + PG restore) | **VERIFIED** (локальный MinIO) / cloud credentials **BLOCKED** |
| YooKassa returns workflow (код + dry_run tests) | **IMPLEMENTED** / live test API **BLOCKED** (SSL timeout до api.yookassa.ru) |
| ProductColor ↔ 1С mapping foundation | **IMPLEMENTED** / GUID характеристики **BLOCKED** (нет в XML) |
| Миграции на изолированных БД | **VERIFIED** |
| Регрессия | см. раздел 5 |
| Git commits блока №4 | см. раздел 6 |

---

## 2. S3 и резервные копии

### Что реализовано

- S3-compatible adapter (`apps/backups/s3.py`, boto3)
- AES-256-GCM RINGOO2 (`crypto_keys.py`) через `BACKUP_ENCRYPTION_KEY*`
- Celery upload / verify / retention (`offsite.py`, `tasks.py`)
- Админка «Внешнее хранилище»
- Инструкция: `docs/ops/OFFSITE_BACKUP_SETUP.md`
- Drill-скрипт: `backend/scripts/block4_offsite_minio_drill.py`

### Реальная проверка (локальный MinIO, не cloud-провайдер)

| Шаг | Результат |
|---|---|
| Провайдер | **MinIO local** (`quay.io/minio/minio`, endpoint `host.docker.internal:19000`) |
| Bucket | `ringoo-backups-drill` (private) |
| Archive ID | `a5225b7a-6bba-4ad3-b4d1-4fd687eaee74` |
| Object key | `ringoo/backups/a5225b7a-…_ringoo_backup_2026-11-06_12-24-25.zip.enc` |
| Size | 209470855 |
| SHA256 match after GET | **True** |
| Tamper reject | **InvalidTag** |
| Decrypt RINGOO2 | **OK** (ZIP `PK`) |
| ZIP entries / manifest / DB dump | 3669 / yes / `database/ringoo.sql` |
| Isolated PG restore DB | `ringoo_restore_drill` |
| Row counts after restore | users=6, orders=23, products=78, payments=13, stock=390 |

**Cloud Yandex/Selectel/AWS:** credentials в `.env` **отсутствуют** → **BLOCKED**.  
Не объявляется как проверка внешнего облачного провайдера.

### Нужно от владельца для cloud offsite

Добавить в локальный `.env` / secret storage (не в чат):

- `BACKUP_OFFSITE_ENABLED=1`
- `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_REGION`, `BACKUP_S3_BUCKET`
- `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`
- `BACKUP_ENCRYPTION_KEY_ID`, `BACKUP_ENCRYPTION_KEY` (копия ключа **вне** VPS)
- опционально `BACKUP_SCHEDULED_ENABLED=1`

---

## 3. Возвраты ЮKassa

### Реализовано

- `apps.returns` FSM, частичные позиции, MoneyRefund, idempotency, dry_run по умолчанию
- Restock только после inspection + `sellable` через `stock_ops.restock_at_store`
- Admin/customer UI
- Исправление: `YooKassaClient()` вместо несуществующего `from_settings()`
- Юр. drafts: `RETURN_*` (не утверждены)
- Drill-скрипты: `block4_yookassa_*_refund_drill.py`

### Проверки

| Проверка | Результат |
|---|---|
| Тестовый ключ (`test_…`) в `.env` | **VERIFIED** |
| `YOOKASSA_TEST_MODE=1`, shop `1518584` | **VERIFIED** |
| Unit/integration dry_run returns tests | **VERIFIED** (в suite) |
| Live GET/POST `api.yookassa.ru` с этой машины | **BLOCKED** — SSL handshake timeout (host + docker) |
| Полный/частичный live refund | **NOT TESTED** (сеть) |
| Webhook live | **NOT TESTED** (сеть) |
| Sber refund | **NEEDS BUSINESS DECISION** (безопасно заблокирован) |

### Юридические решения владельца

См. `RETURN_LEGAL_MATRIX.md` / `RETURN_POLICY_DRAFT.md` — статус **draft**.

---

## 4. 1С / цвета

### Факт по XML `integration1CandKassa/Товары.xml`

- Items: 7679; unique `code`: 3849
- Attrs: `code,name,parentCode,price,quantity,series,seriesID,sklad,skladID,type,typeID`
- Characteristic GUID: **нет**
- Codes on multiple warehouses: **1283**
- Codes with multiple names: **0**

### Реализовано на сайте

- `ProductColor.onec_code`, `onec_characteristic_ref`, `sku`, `barcode`, `mapping_status`
- Admin mapping API; order payload использует matched code
- Запрос владельцу: `docs/audit/ONEC_COLOR_OWNER_REQUEST.md`
- Audit script: `backend/scripts/block4_onec_color_xml_audit.py`

Автосопоставление по названию цвета **не** делается.

---

## 5. Миграции и тесты

### Миграции (не production)

- `backups.0002_offsite_fields` — применена на docker DB
- `products.0007_returns_and_color_mapping` — применена
- `returns.0001_returns_and_color_mapping` — применена (deps: orders.0010, payments.0003)
- Isolated restore DB создана и заполнена из dump

### Зависимость

Добавлено в `requirements.txt`: `cryptography>=42.0.0` (необходимо для RINGOO2).

### Регрессия (факт)

| Проверка | Результат |
|---|---|
| Backend `apps tests integrations` | **532 passed, 9 skipped** |
| PG concurrency | **7 passed** |
| Vitest | **90 passed** |
| `tsc --noEmit` | **exit 0** |
| `next build` | **exit 0** |

---

## 6. Git

Commits созданы в конце этапа (без push). В commit **не** входят: `.env`, `copy-site/`, `integration1CandKassa/`, `*.docx`, `промпт.txt`, SQL dumps, MinIO данные.

---

## 7. Оставшиеся действия владельца

1. **S3 cloud credentials** + offline copy of encryption key → повторить offsite drill на реальном провайдере.  
2. **Сетевой доступ к api.yookassa.ru** (или прогон drill с машины с доступом) → полный/частичный test refund.  
3. **Ответ 1С** по `ONEC_COLOR_OWNER_REQUEST.md`.  
4. **Юр. утверждение** политики возвратов.  
5. Решение по **Sber refund**.
