# Security Remediation Report — Ringoo

| Поле | Значение |
|------|----------|
| Дата | 2026-11-02 |
| Основание | `COMPREHENSIVE_SECURITY_AUDIT_REPORT.md` + ТЗ Critical/High |
| Commit / push / deploy | **Не выполнялись** |
| База | Локальные правки поверх `main` @ `8a0bd5f` |

## 1. Исходные проблемы → результат

См. таблицу §12 ниже.

## 2. Изменённые файлы (основные)

| Файл | Назначение |
|------|------------|
| `backend/config/settings/base.py` | Не грузить `.env.development` в production; OTP default on для production module |
| `backend/config/settings/production.py` | Fail-closed DEBUG/SECRET/HOSTS/OTP/DB/Redis/CORS/CSRF; TRUST_PROXY; убрана деривация SECRET_KEY |
| `backend/config/views.py` | `/health/` без текста исключений |
| `backend/apps/payments/views.py` | Гость: только `order_number` + `phone` |
| `backend/tests/test_payment_security.py` | Тесты SEC-H5 |
| `backend/tests/test_production_settings_security.py` | Контракт production guards |
| `backend/tests/test_sber_payments.py` | Pay API: `order_number` + phone |
| `docker-compose.yml` | Комментарии: prod только с overlay |
| `docker-compose.prod.yml` | Prod-профиль: `!override` / `ports: !reset []`, без bind-mount, без `.env.development` |
| `.env.production.example` | Шаблон секретов (без реальных значений) |
| `frontend/src/lib/api/services/payments.service.ts` | `order_number`, `isOnlinePaymentUiEnabled`, `stashPayAuth` |
| `frontend/src/app/checkout/page.tsx` | Скрытие online; fail на пустой `form_url` |
| `frontend/src/app/orders/[id]/payment/fail\|return/page.tsx` | Согласованный guest auth |
| `docs/ops/*` | Nginx/Caddy, SQL app role |
| `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` | Чек-лист VPS |
| `docs/SECURITY_REMEDIATION_REPORT.md` | Этот отчёт |

Локальные UI-изменения пользователя (home/catalog/и т.д.) **не** перезаписывались, кроме точечных правок checkout/payment.

## 3. Что изменено по пунктам

### SEC-C1 / C2 — PostgreSQL & Redis
- В `docker-compose.prod.yml`: `ports: !reset []` (пустой `ports: []` **не** сбрасывает merge Compose).
- Redis только с `requirepass`; пароли через `${…:?}`.
- Проверено: `docker compose … config --format json` → `db.ports=None`, `redis.ports=None`.
- Dev `docker-compose.yml` по-прежнему публикует порты для GUI. **На VPS обязателен prod overlay.**

### SEC-C3 — .env.development
- `base.py` не вызывает `load_dotenv(.env.development)` при production settings.
- Prod compose: `env_file: !override` → только `.env.production` (required: false, если файла ещё нет).
- Merged config: `.env.development` отсутствует.

### SEC-C4 / H8 — DEBUG & SECRET_KEY
- `DEBUG=True` → `ImproperlyConfigured` в production module.
- Слабый / `django-insecure` SECRET_KEY запрещён (≥48 символов).
- Удалена генерация ключа из публичных идентификаторов.

### SEC-H1 — MFA
- Production требует `ADMIN_OTP_ENABLED` (default on для production module).
- Enrollment TOTP — ручной шаг ops до публикации (см. checklist).

### SEC-H2 — DB least privilege
- Production отвергает user `postgres`/`root`/… и слабые пароли.
- SQL-пример: `docs/ops/postgres_app_role.sql.example` (**не** выполнялся на живой БД).

### SEC-H3 — TLS / proxy
- `TRUST_PROXY=1` включает `SECURE_PROXY_SSL_HEADER`.
- CSRF/CORS обязательны в non-Vercel production.
- Примеры: `docs/ops/caddy.production.example.caddyfile`, `nginx.production.example.conf`.

### SEC-H4 — Compose
- Prod Dockerfile, resource limits, no bind mounts (`!override`).
- Требуется Docker Compose **≥ 2.24** (`!override` / `!reset`).
- Миграции **не** автозапуск — только вручную после бэкапа.

### SEC-H5 / H6 — Guest pay / checkout
- Backend: UUID+phone недостаточно → нужны `order_number` + `phone`.
- FE: online скрыт без `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED=1`; пустой `form_url` → `/payment/fail`.

### SEC-H7 — Backup
- Документация в checklist; **внедрение на VPS = NOT VERIFIED**.

## 4. Тесты (локально, 2026-11-02)

| Проверка | Результат |
|----------|-----------|
| `pytest` (backend `tests/`) | **120 passed, 6 skipped** |
| `pytest apps/users/tests.py` | **23 passed** |
| `manage.py check` (test settings) | **0 issues** |
| `manage.py check --deploy` (production) | **NOT VERIFIED** на этом Windows-хосте: падение импорта `OpenSSL`/`eventlet` (`GEN_EMAIL`) до Django checks — инфраструктура Python, не код Ringoo. Guards покрыты `test_production_settings_security.py`. |
| Production settings subprocess | DEBUG / weak SECRET / postgres user → `IMPROPER` |
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production.example config` | DB/Redis ports unset; no `.env.development`; no bind mounts web/frontend |
| Frontend `npm run type-check` | **OK** |

Реальные платежи / POST в 1С / migrate на prod — **не** выполнялись.

## 5. Оставшиеся риски

- Локальный `docker-compose.yml` публикует DB/Redis — риск только при запуске на VPS **без** prod overlay.
- MFA enrollment нужно выполнить вручную до публикации.
- Backup / SSH / firewall / внешний TLS — только ops на VPS.
- CSP `unsafe-inline` / JWT localStorage fallback — не закрывались полностью (ТЗ §6).
- ONE_C SSRF private-IP deny — не внедрялся (интеграция OFF).
- Полноценный внешний pentest — не проводился.

## 6. Проверки, требующие VPS

Внешний port scan, TLS, SSH hardening, restore drill, live `check --deploy` в prod-образе на сервере, firewall.

## 7. Значения для администратора

См. `.env.production.example` — все `CHANGE_ME_*` заменить. Секреты не коммитить. Не выводить секреты в чат/логи.

## 8–14. Инструкции

См. `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` (запуск, HTTPS, backup, MFA, отключение тестовых режимов перед платежами).

## 12. Таблица статусов

| ID | Проблема | Было | Стало | Тест | Статус |
|----|----------|------|-------|------|--------|
| SEC-C1 | PostgreSQL ports/defaults | Порт наружу, default postgres | Prod: `ports: !reset []`; bootstrap≠app; reject weak | compose config + settings | **FIXED** (prod path); dev ports remain by design |
| SEC-C2 | Redis ports/no auth | Порт наружу, optional password | Prod: `!reset`; requirepass required | compose + settings | **FIXED** (prod path) |
| SEC-C3 | .env.development | Наследование в prod | load_dotenv skip + env_file !override | compose dump + code | **FIXED** |
| SEC-C4 | DEBUG bypass | DEBUG=True обходил checks | DEBUG forbidden in production.py | subprocess tests | **FIXED** |
| SEC-H1 | MFA | Default off | Required in production | settings load | **PARTIALLY FIXED** (code yes; enroll ops) |
| SEC-H2 | DB privileges | App as postgres | Reject postgres user + SQL example | settings contract | **PARTIALLY FIXED** (enforcement yes; role create on VPS) |
| SEC-H3 | TLS/proxy | Header only Vercel | TRUST_PROXY + examples | code + docs | **PARTIALLY FIXED** (needs VPS TLS) |
| SEC-H4 | Compose prod | Incomplete overlay | Full !override / !reset profile | compose config | **FIXED** |
| SEC-H5 | Guest pay UUID+phone | Phone enough | order_number+phone | pytest | **FIXED** |
| SEC-H6 | Empty form_url→success | Success fallthrough | → payment/fail; online gated | code review | **FIXED** |
| SEC-H7 | Backup | Missing | Docs only | — | **NOT VERIFIED** |
| SEC-H8 | SECRET_KEY derive | Public-id fallback | Removed; strong key required | subprocess | **FIXED** |

## Финальный вердикт remediation

**SECURITY REMEDIATION COMPLETE — READY FOR VPS VALIDATION**

Код и prod-конфигурация усилены и проверены локально (pytest, compose config, type-check). Публикация — только после checklist на реальном VPS (порты, TLS, MFA enroll, backup, `check --deploy` в контейнере).
