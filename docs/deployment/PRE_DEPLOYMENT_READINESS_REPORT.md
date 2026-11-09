# PRE-DEPLOYMENT READINESS REPORT — Block 9

Дата: 2026-11-09
Контур: локальная проверка кода + Docker compose config + изолированные тесты.
Живые VPS / PostgreSQL prod / ЮKassa / 1С **не** использовались.

## 1. Общий результат

**Статус: READY WITH CONDITIONS**

Готовность к **контролируемому** развёртыванию staging/soft VPS с выключенными онлайн-оплатой и 1С.
**Не** готов к коммерческой эксплуатации покупателями и **не** готов к боевым ключам ЮKassa / рабочей 1С.

Блокирующих для безопасного GitHub push проблем (секреты в индексе/текущем дереве) не обнаружено.

## 2. Git

| Поле | Значение |
|---|---|
| Исходная ветка | `main` |
| Итоговая ветка | `main` |
| Исходный HEAD (до релизного коммита Block 9) | `d0c047e` (уже +6 к `origin/main` с Block 4) |
| Базовый известный аудит-коммит | `8a0bd5f` (в истории; не HEAD) |
| Remote | `https://github.com/Alikdseq/ringoo.git` |
| Итоговый commit hash | *(заполняется после коммита Block 9)* |
| Push | *(заполняется после push)* |
| Рабочее дерево | после коммита: чистое кроме сознательно исключённых локальных артефактов |

Исключено из релиза: `copy-site/`, `integration1CandKassa/`, `*.docx`, `промпт.txt`, `Описание работ.txt`, локальные `.env*`.

## 3. Безопасность GitHub

| Проверка | Результат |
|---|---|
| Gitleaks / TruffleHog | Не установлены на хосте; выполнен собственный regex/path scan |
| Regex (AWS/GitHub/YK live/Telegram/private key) по diff-кандидатам | clean |
| Реальные `.env` / `backend/.env*` / `frontend/.env.local` | на диске есть, **не** tracked |
| `.env` в Git history (path add) | не найдено |
| `.gitignore` | усилен (env exceptions, dumps/archives, certs, local mirrors) |
| Root `.dockerignore` | добавлен |
| Backend/frontend `.dockerignore` | env исключены |
| Compose secrets | prod через `${VAR:?}` / env_file; без hardcoded production secrets |
| `NEXT_PUBLIC_*` | только публичные URL/флаги/реквизиты организации; приватные ключи ЮKassa/1С не в публичных переменных |
| Hardcoded `SECRET_KEY` в app code | только тестовые stubs в `backend/tests/*` |

Остаточный риск: если когда-либо секреты попали в чужой форк/другой remote — нужна ротация; в текущей ветке `main` path-scan чистый.

## 4. Миграции

| Проверка | Результат |
|---|---|
| Новые файлы в релизе | `payments/0004_payment_refund_line.py`, `products/0008_onec_catalog_synclog.py` |
| `makemigrations --check` (test settings) | N/A — `MIGRATION_MODULES` отключены в `config.settings.test` |
| `makemigrations --check` (development) | Detected **RenameIndex/AlterField drift** (bonus/content/orders/payments/products/stores/wishlist/users) — **не** создавались новые миграции; известный residual |
| Цепочка dependencies 0004/0008 | файлы присутствуют; plan на throwaway SQLite показывает ожидаемые unapplied шаги |
| Рабочая БД | **не** изменялась |

## 5. Production

| Компонент | Оценка |
|---|---|
| Django `production.py` | Fail-closed: DEBUG forbidden, SECRET/hosts/CORS/CSRF/OTP/DB/Redis |
| `check --deploy` в контейнере web | exit 0 при валидных placeholder env (warnings W008/W009/W012/W016/W021 на dummy key / SSL proxy policy) |
| Host Python `check --deploy` | FAIL — конфликт OpenSSL/eventlet на хосте (не код проекта) |
| Next.js | `tsc` OK; `next build` OK |
| Docker compose merge | `docker-compose.yml` + `docker-compose.prod.yml` config OK с placeholder env |
| Prod overlay alone | invalid (ожидаемо; нужен merge) |
| PostgreSQL / Redis | закрыты `ports: !reset []` в overlay |
| Celery | сервисы в compose; локальный celery unhealthy — OPS residual |
| HTTPS | через host reverse proxy; cookies secure defaults в prod |

## 6. Тестирование

| Проверка | Команда | Результат | Комментарий |
|---|---|---|---|
| Backend targeted suite | `python manage.py test` (block8, sec001–003/007, onec, payment security, bank_transfer) — 98 tests | OK | SQLite in-memory; не PG concurrency |
| Frontend typecheck | `npx tsc --noEmit` | OK | |
| Frontend vitest | `npx vitest run` | OK (94) | Исправлен env-isolation в `image-url.test.ts` |
| Frontend build | `npm run build` | OK | example public URLs |
| Compose prod merge config | `docker compose -f …yml -f …prod.yml config` | OK | placeholder env |
| Django check (test) | `manage.py check` | OK | |
| Django check --deploy (container) | `docker exec … check --deploy` | OK | warnings only |
| Live YooKassa / 1С / VPS | — | NOT TESTED | by design |

## 7. Сводка проблем аудитов 1–8 (High/Critical)

| ID | Проблема | Где | Состояние | Доказательство | Остаточный риск |
|---|---|---|---|---|---|
| SEC-001 | Staff bypass customer orders | audit + code | FIXED | `test_sec001_*` OK | — |
| SEC-002 | Unapproved reviews / PII | audit | FIXED | `test_sec002_*` OK | — |
| SEC-003 | Cancel без release резерва | audit | FIXED | `test_sec003_*` OK | — |
| SEC-007 | YooKassa webhook | security block | FIXED | `test_sec007_*` OK | IP filter off until allowlist |
| INV-001 | Плохие цены/qty 1С | Block 8 | FIXED (code+test) | `test_block8_catalog_guards` | Live 1С NOT VERIFIED |
| INV-002 | Refund settlement / reserve | Block 8 | FIXED (code+test) | `test_block8_refund_settlement` | Live refund NOT VERIFIED |
| PAY-001 | Webhook IP empty semantics | Block 8 | FIXED (code+test) | `test_sec007_*` | Allowlist must be set before filter on |
| AUTH/RBAC groups | Staff vs admin | Block 5 report | FIXED (prior) | suite includes admin forbidden cases | Django Admin OTP enroll on VPS |
| bank_transfer API | Disabled method gap | pre-deploy | FIXED | `test_payment_type_bank_transfer_disabled` | — |
| OPS backup/restore | scripts/docs | Block 5 | PARTIALLY FIXED | scripts present | Offsite restore drill NOT VERIFIED |
| INF DB ports | compose base | security | FIXED in prod overlay | `ports: !reset []` | Operator must use overlay |
| RenameIndex drift | makemigrations | pre-deploy | OPEN (accepted) | dry-run lists renames | Do not auto-generate on VPS |
| Live pay/1С | external | all reports | OPEN | flags default off | Business acceptance needed |

## 8. Незакрытые проблемы релиза

| ID | Проблема | Приоритет | Влияние на запуск | Что сделать |
|---|---|---|---|---|
| B9-01 | Live ЮKassa / webhook IP allowlist | HIGH | Блокирует **боевую** оплату, не soft VPS | Staging keys → smoke → allowlist → live |
| B9-02 | Live 1С contract / Beat apply | HIGH | Блокирует каталог из 1С | Согласовать контракт; держать flags=0 |
| B9-03 | Offsite backup restore drill | HIGH | Риск потери данных при аварии | Drill на отдельной БД |
| B9-04 | PG concurrency suite | MEDIUM | Soft OK; race edge | Прогон `test_concurrency_postgres` на PG |
| B9-05 | RenameIndex makemigrations drift | LOW | Шум check | Не применять rename-миграции без нужды |
| B9-06 | Host OpenSSL/eventlet conflict | LOW | Мешает host `check --deploy` | Проверять в контейнере |
| B9-07 | Celery unhealthy locally | MEDIUM | Локальный OPS | На VPS проверить health после deploy |

## 9. Результат GitHub Release

| Поле | Значение |
|---|---|
| Commit создан | *(после шага К–Л)* |
| Push выполнен | *(после шага М)* |
| Commit hash | *(SHA)* |
| Branch | `main` |
| Sync | fast-forward only; no force |

## 10. Следующие действия владельца

1. На VPS: `git clone` / `git pull --ff-only` ветки `main` (см. `PRE_DEPLOYMENT_GITHUB_RELEASE.md`).
2. Создать `.env.production` из example; сильные уникальные секреты; firewall.
3. TLS reverse proxy → `127.0.0.1:3000/8000`.
4. `compose … prod up -d --build` только с overlay.
5. Backup → `migrate` → `collectstatic`.
6. Создать superuser + enroll TOTP.
7. Smoke: `/health/`, витрина, регистрация, заказ **без** онлайн-оплаты.
8. Держать `YOOKASSA_*` / `ONE_C_*` / returns / offsite backup выкл. до отдельных приёмок.
9. Запланировать restore drill и staging payment/1С.

---

**Вердикт:** код можно безопасно опубликовать в существующий GitHub `main` и поднять контролируемый VPS-стенд. Коммерческий запуск магазина и live-интеграции — отдельные этапы после условий выше.
