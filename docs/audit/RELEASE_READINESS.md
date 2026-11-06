# Release readiness — Ringoo (INT-025)

**Дата:** 2026-11-06  
**HEAD на момент аудита/доработок:** `8a0bd5f814fa86e1f09404efb2a886ea1fe879da` (ветка `main`)  
**Commit/push/tag в рамках этапа не выполнялись.**

## 1. Файлы, необходимые для релиза (уверенный список)

### Backend — SEC/FUNC/INT
- `backend/apps/orders/**` (guest_access, services, transitions, serializers, views, admin, migrations 0008–0010)
- `backend/apps/payments/**` (yookassa_service, services, locks, tasks, models, migrations 0002–0003)
- `backend/apps/cart/checkout_clear.py` (+ связанные cart изменения)
- `backend/apps/bonus/signals.py` (+ tests при необходимости)
- `backend/apps/admin_api/views/orders.py` (+ permissions/urls по SEC)
- `backend/apps/content/**` (reviews SEC-002)
- `backend/apps/users/**` (password reset SEC-009)
- `backend/apps/stores/models.py`, `ledger.py`, migration `0007_stockmovement`
- `backend/integrations/yookassa/client.py`
- `backend/integrations/onec/orders.py` (ledger hooks)
- `backend/config/settings/*.py`, `throttling.py`
- `backend/tests/test_sec*.py`, `test_func*.py`, `test_int*.py`, payment/cart related

### Frontend
- checkout / orders detail / payment return / order-status / forgot-password / reset-password
- API services: orders, payments, auth
- types, proxy для payment return

### Docs / ops
- `docs/audit/RINGO_FULL_AUDIT.md`
- `docs/ops/*` (backup, MFA, firewall) — для staging checklist
- `docker-compose.prod.yml`, `.env.production.example`

## 2. Миграции (применить на staging после бэкапа)

| App | Migration | Назначение |
|---|---|---|
| orders | 0008 | checkout_cart_id |
| orders | 0009 | guest_access_token_* |
| orders | 0010 | OrderItem color snapshot |
| payments | 0002 | YooKassa fields |
| payments | 0003 | refund_id / refunded_* (INT-004) |
| stores | 0007 | StockMovement (INT-009) |

Конфликтов графа на диске не ожидается. `migrate` на production — только по отдельному разрешению.

## 3. Переменные окружения (имена, без секретов)

Обязательные prod: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `DJANGO_SETTINGS_MODULE=config.settings.production`.

Платежи (staging test): `YOOKASSA_ENABLED`, `YOOKASSA_TEST_MODE`, `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_RETURN_URL`, `YOOKASSA_WEBHOOK_URL`.

Прочее: `BONUS_ENABLED=0`, `SBER_ECOM_ENABLED=false`, `ONE_C_API_ENABLED`, `LATE_ONLINE_PAYMENT_POLICY`, `PAYMENTS_EXPIRE_LOCK_TTL_SECONDS`, `PAYMENTS_RECONCILE_LOCK_TTL_SECONDS`, SMTP (`EMAIL_HOST*`), `FRONTEND_URL`, `ADMIN_OTP_ENABLED=1`.

## 4. Обязательные тесты перед staging

```
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test python -m pytest -q --no-cov
# целевые: test_int*, test_sec*, test_func*, test_yookassa*, test_payment_security*

cd frontend
npx vitest run
npx next build
```

PostgreSQL concurrency: `tests/test_concurrency_postgres.py` — прогнать при `DATABASE_URL` на Postgres.

## 5. Внешние зависимости

PostgreSQL, Redis, Celery worker+beat, SMTP (guest recover / password reset), YooKassa test shop, reverse proxy (Caddy), опционально 1С test.

## 6. Не включать в релиз

- `.env`, `.env.production` с секретами, локальные ключи
- `backend/.pytest_cache`, `__pycache__`, `celerybeat-schedule`
- `copy-site/**`, временные dumps/logs
- незавершённые/несвязанные черновики → **NEEDS REVIEW**

## 7. Действия для staging (`test.ringoo15.store`)

1. Собрать осознанный commit/tag только из списка выше (вручную, после review).
2. Basic Auth / IP allowlist на test-домене.
3. Backup пустой/тестовой БД → migrate.
4. `YOOKASSA_ENABLED=1`, `YOOKASSA_TEST_MODE=1`.
5. Celery worker + beat.
6. SMTP sandbox.
7. E2E: checkout → pay test → webhook/return → cancel unpaid → reorder color.
8. 1С flags по решению; не live write без согласования.

## 8. Действия для production

Не включать live pay / 1С sync, пока: refund process (бизнес), offsite backup+drill, PG concurrency green, monitoring NEEDS_REVIEW/Celery, TLS/firewall verified.

## 9. Ручные проверки

- [ ] Guest token + email OTP recover  
- [ ] Paid cancel forbidden  
- [ ] Expire + late payment / needs_review UI  
- [ ] Reorder color+store  
- [ ] Admin bulk confirm не оживляет cancelled  
- [ ] Refund webhook (sandbox) → Payment.refunded  
- [ ] Health `/health/`  

## 10. Файлы NEEDS REVIEW (неясная принадлежность)

Любые изменения вне SEC/FUNC/INT/docs из dirty tree (~270+ entries) — разбирать вручную перед commit; не паковать «всё подряд».
