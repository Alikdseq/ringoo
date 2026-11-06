# Спецификация возвратов: деньги и товар (Ringoo)

Статус документа: **черновик для согласования владельцем**. Реальные возвраты и вызовы production API **не выполнялись**.

---

## A. Денежные возвраты (YooKassa / Сбер)

### A.1. Текущая реализация

| Компонент | Поведение |
|-----------|-----------|
| Статусы `Payment` | `created`, `registered`, `pending`, `paid`, `failed`, `expired`, `reversed`, `refunded`, `needs_review` |
| YooKassa `refund.succeeded` | Webhook → `sync_refund_from_yookassa` → **GET `/refunds/{id}`** (не доверие телу) |
| Полный YK refund | Сумма == сумме платежа, payment_id совпал → `STATUS_REFUNDED`, поля `yookassa_refund_id`, `refunded_amount`, `refunded_at` |
| Частичный YK refund | **Не** ставит `refunded`; при бывшем `paid` → `needs_review` |
| `Order.status` при refund | **Не меняется** (явно в коде) |
| Сбер | `getOrderStatusExtended`: status `3` → `reversed`, `4` → `refunded` |
| Late payment на отменённом | Политика `LATE_ONLINE_PAYMENT_POLICY`; для YooKassa `reverse` принудительно `manual` |
| Админ UI | Нет кнопки «вернуть деньги»; только ack `needs_review` → `failed` |
| Отмена оплаченного заказа | Запрещена без `allow_paid`; customer/admin UI не передаёт флаг |
| Идемпотентность YK | По `yookassa_refund_id` |
| Тесты | `backend/tests/test_int004_int005_yookassa_refund_metadata.py` (INT-004 FIXED) |

Источники: `apps/payments/yookassa_service.py`, `services.py`, `models.py`, `eligibility.py`, `admin.py`.

### A.2. Обнаруженные проблемы / пробелы

1. Нет **инициирования** возврата из админки/API (только отражение факта от провайдера).
2. Нет модели **нескольких частичных** возвратов с накоплением остатка.
3. Нет связки **refund ↔ отмена заказа ↔ 1С ↔ склад**.
4. Сбер и YooKassa — разные каналы; при обоих включённых приоритет провайдера у YooKassa.
5. Расхождение «заказ cancelled, деньги ещё paid» — ручной `needs_review` / late policy, не полный refund UX.

### A.3. Предлагаемая архитектура (после решений владельца)

```
Admin/API RefundRequest (идемпотентный ключ)
  → проверка Payment paid / суммы / провайдера
  → вызов API провайдера (YK create refund / Sber refund|reverse по правилам банка)
  → ожидание webhook + обязательный GET статуса
  → Payment + RefundLedger
  → (опционально) Order transition + stock policy (отдельный контур)
```

Требования:

- Идемпотентность по `(payment_id, idempotency_key)`.
- Журнал: кто инициировал, сумма, provider_refund_id, raw status (без PAN).
- Partial: несколько строк ledger; `Payment.refunded` только когда сумма возвратов ≥ суммы платежа (правило утвердить).
- Никогда не менять склад/заказ «молча» из денежного webhook без явного флага политики.

### A.4. Сценарии

| Сценарий | Ожидание (предложение) |
|----------|------------------------|
| Полный возврат | Provider OK → `refunded`; заказ — по политике (cancel / completed+refunded_flag) |
| Частичный | Ledger += amount; order items partial; stock — отдельно |
| Повтор webhook | No-op |
| Отказ провайдера | `needs_review` или `failed` + алерт |
| Уже refunded | 409 / no-op |
| Заказ cancelled, деньги paid | Обязательный денежный refund flow + алерт |

### A.5. Ограничения провайдеров (не смешивать)

**YooKassa:** возвраты через Refund API; webhook `refund.succeeded`; нужна сверка GET; частичные возвраты поддерживаются API, но сайт сейчас их не принимает как финальный `refunded`.

**Сбер:** статусы reverse/refund через Ecom API; late `reverse_order` только в политике late payment; правила окна reverse vs refund — по документации банка (уточнить у эквайера перед live).

### A.6. Решения владельца (блокируют код)

1. Можно ли отменять **оплаченный** заказ из админки с авто-refund?
2. Частичный возврат денег без возврата товара — разрешён?
3. Менять ли `Order.status` при полном refund?
4. Нужен ли отдельный статус заказа `refunded` / `partially_refunded`?
5. Кто инициирует: только суперuser / группа `ringoo_orders` + MFA?
6. Сбер: использовать reverse или refund для «деньги назад после paid»?

---

## B. Физический возврат товара на склад

### B.1. Что уже работает

- Единый слой `stock_ops.py` + `StockMovement`.
- Отмена до передачи: `cancel_order_and_release_stock` → `release_order_item_reservations` (снятие **резерва**, не restock после выдачи).
- Серии: `onec_series_id` на позиции учитывается при release.

### B.2. Чего нет

- Модели заявки на возврат (RMA).
- Операций `restock` / `deduction` в прикладных сценариях (константы есть, вызовов бизнес-потока нет).
- Автоувеличения остатка после «возврата от клиента».
- Связки «брак → не в продажу» vs «годен → в остаток».

### B.3. Предлагаемая модель (не внедрять без решения)

`ReturnRequest` → items (order_item, qty) → reason → condition (`sellable` / `defective` / `to_supplier`) → admin decision → optional money refund ref → stock movement только если `sellable` + approved.

Защита: уникальный `idempotency_key` на `(return_id, item_id)`; запрет qty > купленного − уже возвращённого.

### B.4. Таблица «есть / нет / решить»

| Тема | Статус |
|------|--------|
| Снятие резерва при отмене | Работает |
| Возврат денег (отражение YK full) | Работает частично |
| Инициация refund админом | Нет |
| Физ. возврат после выдачи | Нет |
| Частичный возврат позиций | Нет |
| Брак не в продажу | Нужно решение владельца |
| 1С документ возврата | Нужно решение владельца |

### B.5. Важно

**Не смешивать:** снятие резерва ≠ возврат денег ≠ физическое поступление на склад.

До согласования **нельзя** автоматически увеличивать `Stock.quantity` на любой «возврат».

---

## C. Источники

Код и тесты, перечисленные выше; аудит INT-004 в `RINGO_FULL_AUDIT.md`. Бизнес-правила возврата в документации магазина **не зафиксированы однозначно** → статус **NEEDS BUSINESS DECISION**.
