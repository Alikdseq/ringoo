# Диагностика неуспешной тестовой оплаты ЮKassa

**Дата отчёта:** 2026-11-07
**Режим:** READ ONLY (код/ключи/миграции/платежи не изменялись)
**Проект:** `C:\ringoo`

---

## 1. Последний релевантный платёж (дошёл до hosted page)

Фокус: единственный сегодняшний платёж с непустым `yookassa_payment_id` и `form_url` (пользователь мог ввести карту на стороне ЮKassa).

| Поле | Значение |
|---|---|
| Order number | `ORD-20261107-28733c` |
| Order ID | `e08ad75e-7ebd-435f-b606-db5babd127fd` |
| Order status (сейчас) | `cancelled` |
| Order created (UTC) | `2026-11-07 11:07:50` |
| Payment ID (Django) | `27baa157-a38c-4863-8396-b171ebbf32f8` |
| YooKassa payment ID | `32811a47-000f-5001-9000-151b73a6a65e` |
| Amount | `199800.00 RUB` |
| Payment created (UTC) | `2026-11-07 11:07:50` |
| Payment status (сейчас) | `expired` |
| Provider | `yookassa` |
| is_test (локально) | `True` |
| confirmation type (из ответа ЮKassa) | `redirect` |
| form_url host | `https://yoomoney.ru/checkout/payments/v2/contract` |
| expires_at (в ответе ЮKassa) | `null` |
| payment_method (в ответах ЮKassa) | **отсутствует** |
| paid_at | `null` |
| Local error_message | `Истёк срок оплаты` |
| cancellation_details | **нет** (в сохранённых snapshot) |

### Соседние попытки того же дня (контекст)

Много `POST /pay/` завершились `yookassa_unreachable` **до** создания платежа в ЮKassa (`yookassa_payment_id` пустой, `form_url` пустой) — пользователь на hosted page в этих случаях не попадал.

Пример: `ORD-20261107-3458e7` — 4 failed Payment с `error_code=yookassa_unreachable`.

---

## 2. GET к API ЮKassa (READ-ONLY)

Запрос: `GET /v3/payments/32811a47-000f-5001-9000-151b73a6a65e`
Credentials: тестовые из `.env` (`YOOKASSA_TEST_MODE=1`, shop `1518584`, secret `test_…`). POST не выполнялся.

| Среда | DNS | TCP :443 | TLS | GET payment |
|---|---|---|---|---|
| Windows host | `109.235.165.99` OK | OK | **Timeout** | **URLError SSL handshake timeout** |
| Docker `ringoo_backend` | OK | OK | **Timeout** | **URLError SSL handshake timeout** |

**Живой актуальный статус у ЮKassa сейчас получить нельзя** из-за TLS.

### Что известно из сохранённых ответов API (на момент создания / последней успешной сверки)

`register_response` / `last_status_response` (без секретов):

```json
{
  "id": "32811a47-000f-5001-9000-151b73a6a65e",
  "status": "pending",
  "paid": false,
  "test": true,
  "amount": {"value": "199800.00", "currency": "RUB"},
  "created_at": "2026-11-07T11:07:51.103Z",
  "captured_at": null,
  "expires_at": null,
  "confirmation": {"type": "redirect"},
  "payment_method": null,
  "cancellation_details": null
}
```

Ключевой факт: после попытки оплаты на странице ЮKassa в Ringoo **так и не появился** `payment_method` и статус не стал `succeeded` / `canceled` с `cancellation_details`.

---

## 3. Временная последовательность (backend / celery)

Времена в логах контейнера — локальные (UTC+3) / UTC в БД.

| Время (лок.) | Событие |
|---|---|
| 14:07:50 | Заказ `ORD-20261107-28733c` создан |
| 14:07:50–51 | `payment_creation_started` → `payment_created` `yk_id=32811a47-…`, `POST .../pay/` **200** |
| 14:07:51+ | Пользователь на `yoomoney.ru/checkout/...` (hosted page) |
| 14:11:48 … 14:27:09 | Повторные ошибки сверки: `unreachable` (`gaierror`, `SSLEOFError`, `ConnectionRefusedError`, `TimeoutError`) на `GET /payments/32811a47-…` |
| 14:20:40, 14:23:40, 14:29:40, 14:31:38 | Успешные сверки: `payment_status_checked` → **status=pending** |
| 14:28:50 | Повторный `/pay/` → reuse того же Payment, снова pending |
| 14:31:38 | `expire_unpaid_online_orders`: заказ cancelled (`online_payment_timeout_20m`), Payment → `expired` («Истёк срок оплаты») |
| — | Webhook succeeded для этого платежа в логах **не найден** |

Параллельно в тот же день множество `/pay/` получали **502 Bad Gateway** (`yookassa_unreachable`) из‑за TLS/сети к `api.yookassa.ru`.

---

## 4. Frontend

Сообщение ЮKassa:

> «Не сработало. Похоже, это был технический сбой. Попробуйте ещё раз, пожалуйста»

— это текст **hosted payment page ЮKassa**, не UI Ringoo.

Страница возврата Ringoo: `frontend/src/app/orders/[id]/payment/return/page.tsx`

| Поведение | Факт |
|---|---|
| Успех только при `payment.status === 'paid'` | да |
| `pending` | спиннер «Проверяем / Ожидаем…», polling 3 с |
| `failed` / `expired` / `reversed` / `refunded` | «Оплата не подтверждена» |
| `needs_review` | отдельный экран «на проверке» |
| Сетевая ошибка API статуса | `isError` → friendly error, не «успех» |
| Авто-cancel при unknown | нет; unknown/pending остаются в ожидании |

Вывод: текст «технический сбой» пользователь видел **на стороне ЮKassa до/вместо успешного завершения**, а не как ложную отмену Ringoo.

---

## 5. Сеть

| Проверка | Результат |
|---|---|
| DNS `api.yookassa.ru` | OK |
| TCP 443 | OK |
| TLS handshake (host + docker) | **timeout** (сейчас) |
| HTTP_PROXY / HTTPS_PROXY (host) | не заданы |
| Proxy env в container | пустые значения |
| Изменения VPN/TLS/Docker | **не производились** (READ ONLY) |

Сеть к API нестабильна: в логах celery за час и timeout, и краткие успехи GET, и `ConnectionRefused` / `SSLEOFError`.

---

## 6. Сопоставление (выбор вывода)

**Основной вывод: D** — ошибка на стороне платёжной страницы / ввода карты / тестового сценария ЮKassa.

Доказательства:

1. Платёж в ЮKassa создан корректно (`test: true`, `pending`, redirect URL выдан).
2. После попытки «Заплатить» в сохранённых API-снимках **нет** `payment_method` и **нет** `cancellation_details` — типичный паттерн из `docs/payments/YOOKASSA_INTEGRATION.md`: реальная (не тестовая) карта в test-магазине → UI «технический сбой», API остаётся `pending`.
3. Текст ошибки — стандартный UI ЮKassa, не Ringoo.

**Сопутствующий фактор: B** — Ringoo часто не мог надёжно читать актуальный статус из‑за TLS/сетевых сбоев к `api.yookassa.ru` (`yookassa_unreachable`). Это объясняет 502 на многих `/pay/` и delayed expire, но **не** генерирует текст «технический сбой» на карте.

**Не A:** нет `cancellation_details.reason` в доступных данных.
**Не C:** статус никогда не был `succeeded` / `paid` в Ringoo и в snapshot ЮKassa.

---

## 7. Рекомендуемое исправление (без выполнения в этом отчёте)

1. **Повторить оплату только тестовой картой ЮKassa**, например `5555 5555 5555 4444` (срок любой будущий, CVC любые). Не использовать реальные карты в test-магазине.
2. **Восстановить стабильный TLS** до `api.yookassa.ru` (VPN/firewall/антивирус/ISP), иначе `/pay/`, webhook sync и reconcile будут периодически 502/timeout.
3. После сети — READ-ONLY `GET /payments/32811a47-…` из кабинета ЮKassa или API, чтобы увидеть финальный статус и (если есть) `cancellation_details`.
4. Для новых тестов использовать **малые суммы**, не 199 800 ₽.
5. Не считать return URL доказательством оплаты (уже так в коде).

---

## Резюме

| Вопрос | Ответ |
|---|---|
| Что сломалось для пользователя? | На странице ЮKassa оплата картой не прошла: «технический сбой». |
| Где причина? | Прежде всего **hosted page / тестовая карта (D)**; Ringoo платёж создал верно. Дополнительно **нестабильный TLS к API (B)**. |
| Что в Ringoo? | Заказ создан, Payment зарегистрирован, остался `pending` без `payment_method`, через ~20 мин истёк и заказ cancelled. |
| Что исправить? | Тестовые карты + сеть до API; затем повторить смоук оплаты. |
