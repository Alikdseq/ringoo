# POST-REMEDIATION SECURITY REVIEW — Ringoo

| Поле | Значение |
|------|----------|
| Дата | 2026-11-02 |
| Режим | **READ-ONLY** (код не менялся; исправления не вносились) |
| Объект | Локальное дерево поверх `main` @ `8a0bd5f` |
| Предыдущий отчёт | `docs/SECURITY_REMEDIATION_REPORT.md` |
| Commit / push / deploy / migrate / реальные платежи / POST в 1С | **Не выполнялись** |

## 1. Git

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Ветка / HEAD | `main`, `8a0bd5f` («Document security, 1C…») | **VERIFIED** | Низкий |
| Staged | `git diff --cached` пуст | **VERIFIED** | — |
| Modified / untracked | Массовые M frontend UI + remediations; `??` docs/ops, `.env.production.example`, audits, `.cursor/`, `copy-site/` | **VERIFIED** | Средний: шум в working tree, легко ошибиться при будущем commit |
| Пользовательские UI-правки | Сотни M вне payment/settings/compose сохранены | **VERIFIED** | — |
| Удаления файлов | `git ls-files --deleted` пуст | **VERIFIED** | — |
| Секреты в индексе | Tracked: `.env.example`, `backend/.env.example`; `.env.production` в `.gitignore`; реальных `.env` / ключей в status name-scan нет | **VERIFIED** (поверхностно) | Полный history secret scan — **NOT VERIFIED** |
| `.env.production.example` | Untracked шаблон с `CHANGE_ME_*` (не живые секреты) | **VERIFIED** | Не коммитить заполненный `.env.production` |

## 2. Critical

### SEC-C1 PostgreSQL

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Нет published DB port в **prod merge** | `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production.example config --format json` → `db.ports = None`; `ports: !reset []` в overlay | **VERIFIED** | — |
| Dev compose всё ещё публикует | Dev config: `5436→5432` | **VERIFIED** (by design) | **Высокий**, если на VPS поднять только `docker-compose.yml` |
| Доступ извне иначе | Firewall / `pg_hba` / bind на хосте | **NOT VERIFIED** | Требует VPS |
| Не superuser для app | `production.py` reject `postgres/root/admin/superuser` по **имени** USER в URL/env | **PARTIAL** | Не проверяются реальные GRANT/роли в живой БД |
| Небезопасные defaults | Prod: `${POSTGRES_BOOTSTRAP_PASSWORD:?}`, `${DATABASE_URL:?}`; без env → compose fail (`SECRET_KEY` missing) | **VERIFIED** (prod path) | Dev defaults `postgres/postgres` остаются в `docker-compose.yml` |

### SEC-C2 Redis

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Нет published Redis port (prod) | `redis.ports = None` | **VERIFIED** | — |
| Пароль обязателен | Compose `REDIS_PASSWORD:?` + `requirepass`; `production.py` требует пароль / URL с паролем | **VERIFIED** | — |
| Согласованность REDIS_URL | Example: один и тот же placeholder в `REDIS_PASSWORD` и `REDIS_URL` | **PARTIAL** | Оператор может рассинхронизировать значения вручную |
| Утечка пароля | `redis-server --requirepass "$$REDIS_PASSWORD"`; пароль в env контейнера / возможен в `ps` | **PARTIAL** | Типичный Docker-риск; логи приложения не проверялись end-to-end |
| Dev Redis | Порт `6380`, пароль опционален | **VERIFIED** | Опасен на VPS без overlay |

### SEC-C3 Production environment

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Нет `.env.development` в merge | JSON dump: `has .env.development: False`; `env_file: !override` | **VERIFIED** | — |
| `load_dotenv` в production | `base.py`: при `*.production` грузит только `.env.production` (`override=False`), не development | **VERIFIED** | — |
| Без `.env.production` / секретов | `compose config` без env-file → `required variable SECRET_KEY is missing` | **VERIFIED** | Fail-closed на уровне Compose |
| Service `env_file` при отсутствии файла | `required: false` → в dump `env_file=None`; секреты должны прийти через `--env-file` / shell / созданный файл | **PARTIAL** | Оператор должен явно задать env |

### SEC-C4 / SEC-H8 DEBUG & SECRET_KEY

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| DEBUG=True → fail | `tests/test_production_settings_security.py::test_debug_true_is_rejected` → IMPROPER | **VERIFIED** | — |
| Слабый SECRET_KEY | `test_weak_secret_is_rejected` | **VERIFIED** | — |
| Пустой / короткий KEY | Код: len &lt; 48 / insecure defaults → ImproperlyConfigured | **VERIFIED** (code + weak test) | Отдельный subprocess на empty — не гонялся отдельно |
| ALLOWED_HOSTS пустой | `production.py` raise | **VERIFIED** (code) | Subprocess-тест только на DEBUG/SECRET/postgres |
| Нет derive из public id | Нет hashlib/project-id генерации в `production.py` | **VERIFIED** | — |
| `manage.py check --deploy` | На Windows-хосте падение OpenSSL/eventlet до Django | **NOT VERIFIED** | Повторить в Linux prod-контейнере |

## 3. MFA (SEC-H1)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Флаг обязателен в production | `ADMIN_OTP_ENABLED` false → ImproperlyConfigured; compose `ADMIN_OTP_ENABLED=1` | **VERIFIED** | — |
| OTP wired на Django Admin | `urls.py`: `admin.site.__class__ = OTPAdminSite`; middleware `OTPMiddleware` | **VERIFIED** (code) | Live login без TOTP — **NOT VERIFIED** (нет тестовой среды enroll) |
| Обход альтернативным URL | Один `ADMIN_SITE_URL_PATH`; OTPAdminSite на `admin.site` | **PARTIAL** | Смена URL ≠ MFA; нестандартный path помогает, но не доказан полный lock |
| Все staff/superuser | OTPAdminSite требует verified device для **Django Admin HTML** | **PARTIAL** | **Admin API** (`/api/v1/admin/…`) и Next admin используют JWT/staff permissions **без OTP** |
| Recovery bypass | Отдельного recovery flow в коде не найдено | **PARTIAL** | Стандартный django_otp; ops recovery не документирован как bypass-proof |
| «MFA действительно работает» (как в acceptance remediation) | Нет e2e enroll + login deny | **NOT VERIFIED** | Нельзя считать FIXED end-to-end |

## 4. PostgreSQL least privilege (SEC-H2)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| SQL example | `docs/ops/postgres_app_role.sql.example` — всё **закомментировано**; NOSUPERUSER/NOCREATEDB/NOCREATEROLE; DML + sequences; optional migrate role | **PARTIAL** | Только шаблон, не применён |
| App reject postgres user | Subprocess test + settings | **VERIFIED** (name-level) | Имя `ringoo_app` с SUPERUSER в БД **не** отловится кодом |
| GRANT/REVOKE live | Не выполнялось | **NOT VERIFIED** | — |
| Случайные чрезмерные права | Bootstrap `ringoo_admin` + app URL; ошибка ops возможна | **PARTIAL** | Высокий при неправильном `DATABASE_URL` |

## 5. TLS / reverse proxy (SEC-H3)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Django secure cookies / HSTS / SSL redirect | `production.py`: Secure cookies default True; `SECURE_SSL_REDIRECT` default True (non-Vercel) | **VERIFIED** (code) | Live TLS — **NOT VERIFIED** |
| `TRUST_PROXY` / `SECURE_PROXY_SSL_HEADER` | Включается при `TRUST_PROXY`; prod compose default `TRUST_PROXY=1` | **VERIFIED** | Опасно, если Django публичен напрямую и клиент шлёт `X-Forwarded-Proto` |
| CSRF / CORS обязательны | Raise если пусто (non-Vercel); `CORS_ALLOW_ALL_ORIGINS` запрещён | **VERIFIED** | — |
| Nginx/Caddy examples | `docs/ops/*`; X-Forwarded-Proto https; комментарий не слушать DB/Redis | **PARTIAL** | Примеры, не деплой |
| Обход proxy через published ports | Prod merge публикует **8000** и **3000** | **FAILED** (как конфиг без firewall) | Пока firewall не режет — backend/frontend доступны мимо TLS proxy |
| Axes IP за proxy | `AXES_IPWARE_PROXY_COUNT` default 1 при TRUST_PROXY | **PARTIAL** | Не проверено на живом proxy |

## 6. Guest payment / checkout (SEC-H5 / H6)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| order_number + phone | `_can_access_order`; tests `test_guest_phone_alone_cannot_pay`, gate with both | **VERIFIED** | — |
| Rate limiting | `payment_pay_anon` 20/hour; status/callback throttles | **VERIFIED** (config) | Эффективность vs enumeration UUID — **PARTIAL** |
| Оплата чужого / UUID alone | Owner/staff vs guest tests; 403 | **VERIFIED** | — |
| Подмена order_number | Логика `order.order_number == order_number`; отдельного negative-теста mismatch нет | **PARTIAL** | Поведение корректно по коду |
| Клиент не ставит paid | `test_client_cannot_set_order_paid_via_create_fields`; callback без банка не paid | **VERIFIED** | — |
| Пустой form_url → не success | Checkout → `/payment/fail` | **VERIFIED** (code) | — |
| Sber OFF по умолчанию | Compose `SBER_ECOM_ENABLED=false`; client `_post` raises если disabled | **VERIFIED** | UI hide ≠ API deny; API упирается в disabled client |
| Повторные callback / token | Payment security tests | **VERIFIED** | — |

## 7. `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED`

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Compose передаёт build arg | `docker-compose.prod.yml` args + runtime env `:-0` | **PARTIAL** | — |
| Dockerfile объявляет ARG | `frontend/Dockerfile` **не** содержит `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` | **FAILED** (wiring) | Build-arg из Compose **игнорируется** Docker |
| Попадание в client bundle | Без ARG/ENV на build → `process.env…` пусто → UI OFF (`isOnlinePaymentUiEnabled`) | **PARTIAL** | Fail-closed **случайно**; включить через только runtime env **нельзя** (Next inlines at build) |
| Скрытие UI при OFF | Checkout options + fail page | **VERIFIED** (code) | — |
| Обход через API | `POST /orders/{id}/pay/` остаётся; при Sber OFF → ошибка клиента | **PARTIAL** | При ошибочном `SBER_ECOM_ENABLED=true` UI-флаг не защитит |
| Production frontend build | Не запускался в этом review | **NOT VERIFIED** | — |

## 8. Frontend / backend tests

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Backend full `tests/` | **120 passed, 6 skipped** | **VERIFIED** | Совпадает с remediation |
| Payment / admin / users / production settings | 63 related passed | **VERIFIED** | — |
| TypeScript `npm run type-check` | Exit 0 | **VERIFIED** | — |
| ESLint | 0 errors, **106 warnings** | **PARTIAL** | Не блокирует, но шум security rules |
| Vitest | **14 failed / 16 passed** (54 tests: 10 failed); jsdom/undici errors | **FAILED** | Нельзя подтвердить зелёный FE suite; часть может быть средой, не регрессией remediations |
| Production build FE | Не гонялся | **NOT VERIFIED** | — |

## 9. Docker (SEC-H4)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Compose ≥ 2.24 | `v2.39.4-desktop.1` | **VERIFIED** (локально) | На VPS проверить отдельно |
| DB/Redis ports prod | None | **VERIFIED** | — |
| Bind mounts prod web/frontend | binds `[]` | **VERIFIED** | — |
| Docker socket | Отсутствует в dump | **VERIFIED** | — |
| Non-root | Dockerfile `USER django` / `USER nextjs`; compose `user: null` (наследует image) | **VERIFIED** | db/redis images — vendor default |
| Healthchecks | web/frontend/db/redis yes; celery/beat **нет** | **PARTIAL** | — |
| Resource limits | web/frontend/celery/beat заданы; db/redis нет | **PARTIAL** | — |
| Internal network | `ringoo_network` | **VERIFIED** | — |
| Celery connectivity live | Не поднимался стек | **NOT VERIFIED** | Env указывает на redis URL |
| Prod image build | Не собирался в review | **NOT VERIFIED** | — |

## 10. Backup (SEC-H7)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| Код/скрипты | `scripts/backup-db.sh` и др.: `pg_dump \| gzip` локально; **без** gpg/age/offsite | **PARTIAL** | Default `DB_USER=postgres` в скрипте |
| Encrypted offsite + restore drill | Только checklist / docs | **NOT VERIFIED** | Не заявлять «backup внедрён» |

## 11. Остаточные риски (§6 audit)

| Проверка | Доказательство | Результат | Риск |
|----------|----------------|-----------|------|
| CSP unsafe-inline / unsafe-eval | `config/middleware.py` — HTML unsafe-inline; API docs + unsafe-eval | **VERIFIED** (остаётся) | XSS impact |
| JWT localStorage | Cookie mode default prod; localStorage path остаётся при `USE_AUTH_COOKIES=0`; `token-storage.ts` | **PARTIAL** | XSS → token theft если cookie mode выкл. |
| SSRF ONE_C | Private-IP deny не найден; интеграция OFF по default | **NOT VERIFIED** / residual | При включении 1С |
| `/health/` | Нет текста исключений клиенту; status ok/error | **VERIFIED** | Всё ещё fingerprint DB/cache down |
| Axes proxy | См. выше | **PARTIAL** | — |
| Admin audit | `apps.audit` существует | **PARTIAL** | Полнота покрытия staff actions — не аудитилась |
| Git history secrets | Не tool-сканировался | **NOT VERIFIED** | — |
| Argon2 | `PASSWORD_HASHERS` Argon2 first | **VERIFIED** | — |

## 12. Сводка vs заявления remediation agent

| ID | Заявление remediation | Независимый статус |
|----|----------------------|--------------------|
| SEC-C1 | FIXED | **VERIFIED** для prod overlay; dev ports остаются |
| SEC-C2 | FIXED | **VERIFIED** для prod overlay |
| SEC-C3 | FIXED | **VERIFIED** |
| SEC-C4 | FIXED | **VERIFIED** (subprocess); check --deploy host **NOT VERIFIED** |
| SEC-H1 | PARTIALLY FIXED | Подтверждено: **PARTIAL / NOT VERIFIED** e2e; admin_api без OTP |
| SEC-H2 | PARTIALLY FIXED | Подтверждено |
| SEC-H3 | PARTIALLY FIXED | Подтверждено; **FAILED** published 8000/3000 без firewall |
| SEC-H4 | FIXED | **PARTIAL** (limits/health celery; image build не гонялся) |
| SEC-H5 | FIXED | **VERIFIED** (pytest + code) |
| SEC-H6 | FIXED | **VERIFIED** code; ONLINE_PAYMENT Dockerfile wiring **FAILED** |
| SEC-H7 | NOT VERIFIED | Подтверждено |
| SEC-H8 | FIXED | **VERIFIED** |

## 13. Что нельзя считать закрытым до VPS

1. Firewall: закрыть 5432/6379 **и** по возможности не публиковать 8000/3000 наружу (только 80/443 → proxy → localhost).
2. Enroll TOTP для Django Admin + политика для staff API (OTP не закрывает `/api/v1/admin`).
3. Создать роль `ringoo_app` и проверить `\du` / privileges.
4. TLS + `check --deploy` внутри контейнера.
5. Encrypted offsite backup + restore drill.
6. Починить/разобрать красный Vitest до регрессионной уверенности по FE.
7. Добавить `ARG`/`ENV` `NEXT_PUBLIC_ONLINE_PAYMENT_ENABLED` в `frontend/Dockerfile`, если флаг должен управляться осознанно (сейчас OFF по умолчанию).

---

## Финальный вердикт

**SECURITY CONDITIONAL**

Critical prod-path (DB/Redis ports reset, no `.env.development`, DEBUG/SECRET fail-closed, guest pay gate, Sber/1С OFF defaults) **подтверждены** локально.  
Не подтверждены как «готово к открытию»: MFA end-to-end для всех admin-путей, least-privilege в живой БД, TLS/firewall против published app ports, backup, FE Vitest, production image builds.

Не **READY FOR PUBLIC DEPLOYMENT**.  
К следующему шагу **VPS validation** можно переходить только с явным firewall/TLS/MFA-enroll планом; до закрытия замечаний выше статус остаётся условным, не «remediation complete без оговорок».
