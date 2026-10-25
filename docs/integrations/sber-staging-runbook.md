# Runbook: staging / тест Сбер ecom

Цель: подготовить контур к реальному тесту оплаты картой **без** кассы и без заказов в 1С.

**Реальные платежи на шлюзе не считаются проверенными**, пока не выданы тестовые доступы и не пройден §5.

## 0. Перед деплоем (репозиторий)

Код `backend/apps/payments/`, `backend/integrations/sber/` и доки интеграций должны быть **закоммичены и задеплоены** на staging. Без этого `migrate payments` на сервере не найдёт приложение.

## 1. Миграции

```bash
cd backend
python manage.py migrate payments
python manage.py showmigrations payments
```

Ожидается: `[X] 0001_initial`. Таблица `payments_payment` (в т.ч. статус `needs_review` в choices).

Преflight без секретов и без вызова банка:

```bash
python manage.py check_sber_staging
# В день теста с доступами:
# python manage.py check_sber_staging --require-enabled --require-credentials
```

## 2. Переменные окружения (staging)

Скопировать из `backend/.env.example` в env контейнера/`backend/.env` на staging:

| Переменная | Значение |
| --- | --- |
| `SBER_ECOM_BASE_URL` | `https://ecomtest.sberbank.ru` |
| `SBER_ECOM_USERNAME` | логин `*-api` от Сбера |
| `SBER_ECOM_PASSWORD` | пароль |
| `SBER_ECOM_ENABLED` | `true` только в день теста на staging |
| `SBER_ECOM_ALLOW_PRODUCTION` | **не задавать** / `false` (блок epay) |
| `FRONTEND_URL` | публичный **https** URL витрины |
| `SBER_ECOM_CALLBACK_URL` | `https://<api-host>/api/v1/payments/sber/callback/` |
| `ONLINE_PAYMENT_TIMEOUT_MINUTES` | `20` (или согласованное) |
| `LATE_ONLINE_PAYMENT_POLICY` | `manual` до решения бизнеса; затем `revive` или `reverse` |

Опционально явные return/fail (иначе `{FRONTEND_URL}/orders/{order_id}/payment/return|fail`):

- `SBER_ECOM_RETURN_URL`
- `SBER_ECOM_FAIL_URL`

Бой (`https://epay.sberbank.ru`) **не** включать. Клиент откажет без `SBER_ECOM_ALLOW_PRODUCTION=true`.

В Docker Compose (локально/staging на compose) сервисы `web`, `celery`, `celery-beat` читают `backend/.env.development` — добавьте туда же переменные Сбера (не коммитьте секреты).

## 3. Callback (публичный HTTPS)

1. Backend доступен с интернета по HTTPS (staging или ngrok).
2. Пример ngrok: `https://xxxx.ngrok-free.app/api/v1/payments/sber/callback/`
3. Тот же URL в `SBER_ECOM_CALLBACK_URL` и в ЛК Сбера (если требуется).
4. Return/fail с ПШ должны открывать **публичный** фронт (не `localhost`).
5. `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` должны включать хост API и фронта.

Проверка приёмки callback (без реального платежа):

```bash
curl -X POST https://<api>/api/v1/payments/sber/callback/ \
  -H "Content-Type: application/json" \
  -d '{"mdOrder":"00000000-0000-0000-0000-000000000000","operation":"deposited","status":1}'
```

Ожидается HTTP 200 `{"ok":true,"found":false}`.

## 4. Фоновые задачи

Нужен **Celery worker + beat** (в `docker-compose.yml` есть `celery` и `celery-beat`) **или** cron:

```bash
python manage.py expire_unpaid_online_orders
python manage.py reconcile_open_payments --older-than-minutes 2
python manage.py monitor_hung_payments --fail-on-findings
```

Beat (из settings): expire каждые 5 мин, reconcile каждые 3 мин.

Проверка процессов (Docker):

```bash
docker compose ps web celery celery-beat
docker compose logs --tail=50 celery-beat
```

`docker-compose.prod.yml` только меняет команду web/frontend — celery/beat остаются из базового compose; поднимайте их вместе:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web celery celery-beat frontend
```

## 5. Smoke после выдачи доступов

Предварительно: `SBER_ECOM_ENABLED=true`, учётки, HTTPS callback/фронт, `check_sber_staging --require-enabled --require-credentials`.

1. Создать заказ с `payment_type=online` (витрина или API).
2. `POST /api/v1/orders/{id}/pay/` с телефоном гостя при необходимости → `form_url`.
3. Оплатить **тестовой** картой из документации Сбера (ecomtest).
4. Вернуться на `/orders/{id}/payment/return` → `payment.status=paid`, заказ `confirmed`.
5. Повторно отправить callback с тем же `mdOrder` — идемпотентность, статус остаётся `paid`.
6. Новый заказ: не завершать оплату → после timeout (`ONLINE_PAYMENT_TIMEOUT_MINUTES`) заказ `cancelled`, резерв снят (expire/beat).
7. (Опц.) Оплата после cancel → `needs_review` или reverse/revive по `LATE_ONLINE_PAYMENT_POLICY`.
8. Fail-страница: «Оплатить снова» (нужен телефон в sessionStorage с checkout).

**Не** переключать BASE_URL на epay в этом прогоне.

## 6. Мониторинг

```bash
python manage.py monitor_hung_payments --json
python manage.py monitor_hung_payments --fail-on-findings
```

- Админка Django: платежи «Требует сверки».
- Логи (без паролей): `Paid after cancel`, `Sber register failed`, `amount mismatch`.

## 7. Откат

```bash
# в env staging
SBER_ECOM_ENABLED=false
```

Клиент не ходит в сеть; новые online-оплаты получат ошибку регистрации.

## 8. Чек-лист «можно звать Сбера на тест»

- [ ] Код payments/sber задеплоен
- [ ] `migrate payments` применён
- [ ] `celery` + `celery-beat` (или cron) работают
- [ ] `FRONTEND_URL` и callback — публичный HTTPS
- [ ] Тестовые `USERNAME`/`PASSWORD` получены
- [ ] `SBER_ECOM_ENABLED=true`, BASE_URL = ecomtest, `ALLOW_PRODUCTION` выключен
- [ ] `check_sber_staging --require-enabled --require-credentials` без ERR
