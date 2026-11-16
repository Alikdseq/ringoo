# RELEASE 39 — DOUBLE PAYMENT PREVENTION + EXTERNAL REFUND POLICY

**Дата:** 2026-11-16  
**Основание:** RELEASE 38 = PASS WITH WARNINGS  
**Вердикт:** **PASS WITH WARNINGS**

Локальные исправления R38-R1 / R38-R2 выполнены. Это **не** go-live: нет live YooKassa cancel API в клиенте; staging/IP allowlist по-прежнему вне scope.

---

## 1. Branch / HEAD / дерево

| | |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| Working tree | dirty (R8–R38 + R39); чужие изменения сохранены |
| Git ops | нет |

---

## 2. Повторное создание платежа — до R39

1. Active `registered/pending` → sync → reuse (уже было).
2. Локальный `failed`/`expired` **без** обязательной сверки «ещё жив ли URL у ЮKassa» → новый `Payment` + новый `create_payment` → **вторая confirmation URL**.
3. `expire_unpaid_online_orders` ставил `EXPIRED` локально, **не** отменяя платёж у провайдера (в клиенте нет cancel API).
4. Timeout на create → `FAILED` без `yookassa_payment_id` → новый row с **новым** Idempotence-Key.

Комментарий в коде уже признавал: после local cancel mapping старый URL у ЮKassa «может ещё жить».

---

## 3. Может ли старая confirmation URL оставаться рабочей?

**Да** — пока у ЮKassa статус `pending` / `waiting_for_capture`. Локальный `expired`/`failed` этого не отменяет.

В репозитории **нет** метода `POST /payments/{id}/cancel` и нет внутренней документации на cancel. По правилу «не придумывать API» отмена у провайдера **не** добавлялась.

---

## 4–5. Как теперь закрывается старая сессия / когда разрешён новый платёж

`_resolve_prior_yookassa_sessions` **до** нового create:

| Результат GET | Действие |
|---|---|
| `pending` / `waiting_for_capture` | **Reuse** той же сессии (восстановить `form_url` из payload при необходимости) |
| `canceled` | Сессия закрыта → можно создать **новый** Payment |
| `succeeded` | `already_paid` |
| unreachable / error | `payment_status_unknown` — **новый create запрещён** |
| `needs_review` / `reversed` / `refunded` | `payment_blocked` |

Дополнительно:

- `FAILED` **без** `yookassa_payment_id` → retry того же row (тот же Idempotence-Key), не новый UUID.
- Expire очищает `form_url` локально (ссылку клиенту не отдаём), но новый create всё равно требует confirmed `canceled` или reuse pending.

---

## 6. Timeout и неизвестный статус

- Недоступность GET по существующему `yookassa_payment_id` → 503 `payment_status_unknown`, без новой сессии.
- Timeout create без id → повтор с тем же Payment id / Idempotence-Key.

---

## 7. Конкурентные тесты

| Покрытие | Результат |
|---|---|
| Existing `test_concurrency_postgres` (parallel sync) | NOT RUN в R39 (destructive/env) — опираемся на R38 inventory |
| `test_unknown_status_does_not_create_second_payment` | PASS |
| R39: expired+pending reuse; failed+pending reuse; unreachable block; canceled→new | PASS |
| Parallel create | сериализация `select_for_update` на order (без изменений схемы) |

---

## 8. Старый webhook после нового платежа

- Unique `payments_one_paid_per_order` + sync duplicate → второй remote success локально failed/needs_review.
- Если старая сессия ещё pending и пользователь платит по старой ссылке до confirmed cancel — деньги могут уйти на старый payment; локально станет paid. Новый pending останется; eligibility заблокирует второй paid. **Ops:** сверка/ручной refund в ЛК (вне Ringoo).

---

## 9–10. Входящий `refund.succeeded` (R38-R2)

**Новое поведение:**

1. GET `/refunds/{id}` (как раньше) — без `create_refund`.
2. Идемпотентная запись `PaymentRefund`.
3. Полная сумма → `Payment.status=needs_review` + сообщение о внешней сверке.
4. **Нет** `cancel_order_and_release_stock`.
5. **Нет** изменения `Order.payment_status` / `Order.status`.
6. **Нет** изменения reserve/quantity.
7. Частичные суммы по-прежнему копятся без отмены заказа.

`_release_reservation_after_full_refund` больше **не вызывается** из webhook path (функция сохранена, но отключена от автопотока).

---

## 11. Инициация возвратов (R38)

Без ослабления: `PAYMENTS_REFUND_INITIATION_ENABLED` / production force / client guards / returns API. Тесты R38 зелёные.

---

## 12. Изменённые файлы

- `apps/payments/yookassa_service.py` — resolve prior sessions; external refund policy
- `apps/payments/services.py` — expire clears `form_url`
- `apps/payments/views.py` — HTTP 409 для `payment_session_active`
- `tests/test_r39_double_charge_and_external_refund.py` (new)
- `tests/test_block8_refund_settlement.py`
- `tests/test_int004_int005_yookassa_refund_metadata.py`
- `tests/test_order_repay.py`
- `tests/test_r38_refund_initiation_disabled.py`
- этот отчёт

---

## 13. Тесты

| Набор | Результат |
|---|---|
| R39 + block8 + int004/005 + repay + r38 + yookassa_payments | **69 passed** |
| sec007 + func001 + func011 + online_cart + payment_security | **70 passed** |
| Django check / makemigrations | OK |
| Black / isort (изменённые) | OK |
| flake8 (critical selects) | OK |

**NOT RUN:** live YooKassa, cancel API, drills, concurrency postgres, full pytest.

---

## 14. Не проверенные сценарии

- Реальная отмена платежа в ЛК ЮKassa / API cancel (нет в клиенте).
- Две живые ссылки, оплаченные обе на стороне провайдера (ops).
- Production IP allowlist.
- Sber sync-before-reuse (R38-R6) — не в scope R39.

---

## 15. Остаточные риски

| ID | Crit | Описание | Действие |
|---|---|---|---|
| R39-R1 | MEDIUM | Нет provider cancel — закрытие сессии только когда ЮKassa сама `canceled` | При необходимости добавить cancel по доке ЮKassa отдельным релизом |
| R39-R2 | MEDIUM | Пользователь может оплатить старую ссылку, пока remote pending | Мониторинг; не создавать новую до cancel; runbook |
| R39-R3 | LOW | `Order.payment_status` остаётся `paid` при внешнем refund → needs_review на Payment | Ручная сверка в админке |
| R38-R3 | MEDIUM | Webhook IP filter off by default | Staging/prod checklist |
| R38-R6 | MEDIUM | Sber reuse без sync | Отдельный релиз если Sber live |

---

## Однозначные ответы

| Вопрос | Ответ |
|---|---|
| Две активные платёжные ссылки от Ringoo? | **Не должны:** пока remote pending — reuse; новый create только после confirmed `canceled` |
| Старая ссылка после «новой»? | Новую не создаём, пока старая pending. Если когда-то создали до R39 — старая может быть жива у провайдера |
| Недоступность YooKassa? | Нет новой сессии; `payment_status_unknown` |
| Новый платёж без закрытия предыдущей? | **Нет** (для сессий с `yookassa_payment_id`) |
| Старый webhook vs новый платёж? | Второй paid локально блокируется; деньги на провайдере — ops |
| Refund webhook авто-отменит заказ? | **Нет** |
| Освободит резерв? | **Нет** |
| Ringoo инициирует возврат в production? | **Нет** (R38 gates) |
| Орг. ограничения ЛК ЮKassa? | Минимальные права; без self-service refund для линии поддержки; журнал ручных возвратов; сверка с `needs_review` |

---

**Стоп.** Commit / push / deploy не выполнялись.
