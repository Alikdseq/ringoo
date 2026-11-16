# RELEASE 38 — FULL PAYMENT FLOW AUDIT + REFUNDS DISABLED FOR PRODUCTION

**Дата:** 2026-11-16  
**Основание:** RELEASE 37 = PASS WITH WARNINGS  
**Вердикт:** **PASS WITH WARNINGS**

Локальный аудит и hardening завершения. Это **не** go-live approval: staging/production-конфиг и live webhook IP требуют отдельной проверки на сервере.

---

## 1. Вердикт

**PASS WITH WARNINGS**

- Критичный контур оплаты (create → webhook GET → paid → cart clear) локально согласован и покрыт тестами.
- **Инициация денежных возвратов** в production **жёстко запрещена** на backend (не только UI).
- Входящие `refund.succeeded` **не инициируют** новый возврат; по-прежнему делают GET и отражают факт (см. риски авто-cancel).
- Остаточные риски: double confirmation URL у провайдера, webhook IP filter по умолчанию выкл, ручной refund в ЛК ЮKassa.

---

## 2. Branch / HEAD / дерево

| | |
|---|---|
| Branch | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| Working tree | dirty (R8–R37 + R38); чужие изменения сохранены |
| Git ops | нет |

---

## 3. Инвентаризация платёжной архитектуры

| Слой | Компоненты |
|---|---|
| API | `OrderPayView` `POST /api/v1/orders/{id}/pay/`; status/return sync views |
| YooKassa | `initiate_yookassa_payment`, `sync_payment_from_yookassa`, `handle_yookassa_webhook`, `sync_refund_from_yookassa` |
| Sber | `apps/payments/services.py` initiate/sync; `reverse_order` / `refund_order` (теперь gated) |
| Eligibility | `evaluate_order_payment_eligibility` / `assert_order_payable_or_raise` |
| Cart | `clear_cart_after_successful_payment` (on_commit после paid) |
| Returns product | `apps.returns` + Admin API; flag `RETURNS_ENABLED` |
| Client libs | `integrations/yookassa/client.py`, `integrations/sber/client.py` |

Провайдер выбирается через `online_payment_provider()`; сумма **только** из `Order.total_amount`.

---

## 4. Создание платежа

1. Auth: владелец JWT или guest token (SEC-006); staff не платит чужие заказы.
2. `assert_order_payable_or_raise` — online, не cancelled/fulfilled/ready, не already paid, нет blocking payment, provider enabled.
3. `select_for_update` на order + reuse active `registered/pending` с form_url; иначе dangling `created` или новый row.
4. HTTP create **вне** DB transaction; `idempotence_key=str(payment.id)`.
5. Ошибка API → payment `failed`, клиенту ошибка без form_url.
6. Ответ: `form_url` / confirmation URL.

---

## 5. Повторные и параллельные запросы

| Сценарий | Поведение |
|---|---|
| Повтор pay | YooKassa: reuse после **sync** с провайдером; Sber: reuse form_url **без** sync-before-reuse (слабее) |
| Параллельные | `select_for_update` сериализует создание row |
| Уже paid | `already_paid` / eligibility |
| Failed/expired active | form_url очищается, создаётся новый |
| Две confirmation URL | Возможны после recreate; локально второй `paid` режется unique/select_for_update |

**Риск двойного списания на стороне провайдера** при двух живых сессиях — **остаточный** (R38-R1). Локальная защита ≠ гарантия одного capture у ЮKassa/Sber.

Доп. из inventory ([Payment flow inventory](68bc95b9-b360-435d-b922-9e57300e6dc1)): Sber может вернуть stale `form_url`, пока банк уже paid — ловится status poll/callback, но слабее YK sync-before-reuse (R38-R6).

---

## 6. Успешная оплата

- Webhook/return **не** доверяют телу: обязателен GET payment.
- INT-005: metadata order_id/payment_id + amount + currency + id.
- `select_for_update`; early return если уже paid; отказ при другом paid на заказе.
- `Order.payment_status=paid`; cart clear on_commit; enqueue 1С sync.
- Повтор webhook — идемпотентен.

---

## 7. Неуспешная оплата

- canceled/expired/failed → не paid; cart **не** чистится.
- Можно повторно pay после закрытия предыдущего платежа (eligibility).
- Заказ и состав сохраняются.
- Повторный error webhook не переводит в paid.

---

## 8. Webhook и повторная обработка

- Events: `payment.succeeded|waiting_for_capture|canceled`, `refund.succeeded`.
- IP: `YOOKASSA_WEBHOOK_IP_ALLOWLIST` + `YOOKASSA_WEBHOOK_IP_FILTER_ENABLED`; проверка **только `REMOTE_ADDR`**, не сырой `X-Forwarded-For`.
- Пустой allowlist + filter off → IP не проверяется (warning once); authenticity = provider GET.
- Debounce снижает нагрузку, не единственная защита.
- Исключения в refund path → `None` / без ложного paid (R37).

---

## 9. Статусы

| Поле | Роль |
|---|---|
| `Order.status` | FSM fulfillment (new/processing/ready/closed) |
| `Order.payment_status` | unpaid / paid / refunded |
| `Payment.status` | created→…→paid / failed / expired / refunded / needs_review / … |

Отмена неоплаченного ≠ refund. Отмена оплаченного без refund flow запрещена (`allow_paid`).

---

## 10. Корзина, остатки, резерв

- Cart clear только после confirmed paid (product+color+store; idempotent).
- Fail/cancel payment — корзина цела.
- Резерв при создании заказа; release при cancel / full external refund settlement (unshipped).
- Quantity склада при YK full refund **не** увеличивается (INV-002).

---

## 11. Полный список механизмов возврата

| # | Механизм | Инициация? | Production |
|---|---|---|---|
| 1 | `YooKassaClient.create_refund` | Да | **BLOCKED** (`assert_refund_initiation_allowed`) |
| 2 | `SberEcomClient.refund_order` | Да | **BLOCKED** |
| 3 | `SberEcomClient.reverse_order` | Да (деньги/удержание) | **BLOCKED**; late-policy → needs_review |
| 4 | `initiate_money_refund(..., dry_run=False)` | Да | **BLOCKED** |
| 5 | Admin `POST .../returns/<id>/refund/` | Да | **403** если `RETURNS_ENABLED=0` (production force); live call тоже blocked |
| 6 | Customer returns API | Заявка | **403** / UI 404 |
| 7 | Django Admin ReturnRequest | UI | Не регистрируется при flag off |
| 8 | Next Admin `/admin/returns` | UI | `NEXT_PUBLIC_RETURNS_ENABLED=0` → 404 |
| 9 | Drill scripts `block4_*refund*` | Да | Не для prod; client всё равно blocked under production settings |
| 10 | Celery/management refund tasks | — | **Не найдены** |
| 11 | `sync_refund_from_yookassa` / webhook `refund.succeeded` | **Нет** (только GET+запись) | Разрешено как отражение внешнего факта |
| 12 | Ручной возврат в ЛК ЮKassa | Вне app | Ожидаемый бизнес-процесс этапа 1 |

---

## 12. Блокировка возвратов в production

| Контроль | Поведение |
|---|---|
| `PAYMENTS_REFUND_INITIATION_ENABLED` | Default **False** (base) |
| `config.settings.production` | **Принудительно** `PAYMENTS_REFUND_INITIATION_ENABLED=False` и `RETURNS_ENABLED=False` (env не открывает) |
| Client POST refund/reverse | Exception `RefundInitiationDisabled` до HTTP |
| Returns HTTP | 403 `returns_temporarily_disabled` |
| UI | `NEXT_PUBLIC_RETURNS_ENABLED` default 0 |

---

## 13. Прямые API и admin

- Customer/admin returns routes существуют, но gated.
- Обход UI прямым HTTP при production settings → 403 / client assert.
- dry_run=True в сервисе не зовёт провайдера; dry_run=False → block.

---

## 14. Фоновые задачи и внутренние сервисы

- Celery refund initiate: не найдено.
- Late Sber reverse: при выкл. initiation → `needs_review`, **без** API reverse.
- Webhook refund: только GET + local state (может cancel unshipped — см. R38-R2).

---

## 15. Webhook security / IP allowlist

| Вопрос | Ответ |
|---|---|
| IP check? | Опционально |
| Source IP | `REMOTE_ADDR` only |
| X-Forwarded-For spoof? | Не используется для allowlist (хорошо при корректном proxy) |
| Trusted proxy | `TRUST_PROXY` / axes ipware — отдельно; webhook allowlist не читает XFF |
| Empty allowlist | Filter off → allow all IPs; paid всё равно через GET |
| Env vars (имена) | `YOOKASSA_WEBHOOK_IP_ALLOWLIST`, `YOOKASSA_WEBHOOK_IP_FILTER_ENABLED` — значения не читались |

**Staging/prod checklist:** включить filter + заполнить allowlist ЮKassa; убедиться, что proxy ставит реальный peer в `REMOTE_ADDR`.

---

## 16. Найденные дефекты / gaps

| ID | Severity | Описание |
|---|---|---|
| R38-D1 | HIGH (fixed) | Инициация refund возможна через client/service в обход UI flags |
| R38-R1 | HIGH | Две payment sessions / риск double capture у провайдера |
| R38-R2 | MEDIUM | Входящий полный refund авто-cancel + release reserve для new/processing |
| R38-R3 | MEDIUM | IP filter off by default |
| R38-R4 | LOW | Late reverse отключён → ручная сверка needs_review |
| R38-R6 | MEDIUM | Sber reuse active form_url без sync-before-reuse (слабее YK) |

R37 refund rollback при `payment_status=paid` — уже исправлен ранее.

---

## 17. Выполненные исправления

1. `apps/payments/refund_policy.py` — единый gate.
2. Guards: YooKassa `create_refund`, Sber `reverse_order`/`refund_order`, `initiate_money_refund` (non-dry-run).
3. `apply_late_payment_policy` reverse → needs_review если initiation off.
4. `production.py` force-disable returns + initiation flags.
5. `.env.example`, `.env.production.example`, `docker-compose.prod.yml` documentation defaults.
6. Admin refund view maps `RefundInitiationDisabled` → 403.

---

## 18. Добавленные / обновлённые тесты

- `tests/test_r38_refund_initiation_disabled.py` — flag, create_refund block, sber block, initiate_money_refund, inbound webhook без create_refund.
- `tests/test_sber_payments.py` — override для reverse; новый `test_late_policy_reverse_blocked_when_initiation_disabled`.

---

## 19. Результаты тестов (локально, mock)

| Набор | Результат |
|---|---|
| R38 + block8 + int004/005 + repay + sber reverse/late + returns | **53 passed** |
| yookassa + sec007 webhook + func001 expire + func011 cart + admin auth | **47 passed** |
| Django check / makemigrations | OK |
| Black / isort (изменённые) | OK |
| flake8 изменённых | только pre-existing C901 |

**NOT RUN:** live YooKassa, live Sber, production DB, drill scripts, concurrency postgres, full pytest.

---

## 20. Непроверенные сценарии

- Реальный double-pay в ЛК ЮKassa с двумя URL.
- Production IP allowlist + TLS terminator.
- Параллельные webhook на Postgres under load.
- Sber live reverse/refund.
- 1С реакция на cancel после external refund.

---

## 21. Оставшиеся риски

| ID | Crit | File/fn | Scenario | Impact | Action |
|---|---|---|---|---|---|
| R38-R1 | HIGH | `initiate_yookassa_payment` | Recreate после fail → 2 URL | Double capture у провайдера | Ops: не оставлять две сессии; мониторинг; staging drill |
| R38-R2 | MEDIUM | `_release_reservation_after_full_refund` | External full refund webhook | Auto cancel + release | Подтвердить бизнес-OK; иначе needs_review-only mode |
| R38-R3 | MEDIUM | `yookassa_webhook_ip_allowed` | Filter off | Abuse load / probe | Enable allowlist on VPS |
| R38-R4 | LOW | `apply_late_payment_policy` | Late paid + reverse policy | Manual ops | Document runbook |
| R38-R5 | LOW | Frontend legal copy | «возврат» в оферте | Не API | Ожидаемо (офлайн) |
| R38-R6 | MEDIUM | `initiate_sber_payment` reuse | Reuse form_url без sync-before-reuse | Stale URL / late bank paid | Если Sber включён: усилить sync-before-reuse (отдельный релиз) |

---

## 22. Staging / production checklist (без доступа к серверу)

1. `DJANGO_SETTINGS_MODULE=config.settings.production`.
2. Подтвердить `RETURNS_ENABLED=0`, `PAYMENTS_REFUND_INITIATION_ENABLED=0`, `NEXT_PUBLIC_RETURNS_ENABLED=0` (rebuild frontend).
3. `YOOKASSA_WEBHOOK_IP_FILTER_ENABLED=1` + allowlist официальных IP.
4. `TRUST_PROXY` / real IP корректны.
5. Staging: один заказ → pay → succeed → cart clear; fail path без clear.
6. Staging: POST admin/returns/refund → 403.
7. Staging: mock/create_refund path raises / blocked.
8. Ручной refund в тест-ЛК ЮKassa → webhook отражает статус **без** второго create_refund.
9. Мониторинг `needs_review` и late-payment.

---

## Однозначные ответы

| Вопрос | Ответ |
|---|---|
| Можно ли создать два платежа на один заказ? | Да, последовательно после fail/expire; параллельно сериализуется; два paid локально блокируются |
| Риск двойного списания? | **Да, остаточный у провайдера** при двух confirmation URL |
| Ошибочно отметить paid? | Маловероятно без успешного GET + metadata/amount match |
| Повторный webhook повторит side effects? | Нет (idempotent paid/refund) |
| Неуспех очистит корзину? | Нет |
| Оплата сломает остатки? | Paid не restock’ает; reserve по правилам заказа |
| Возвраты в production полностью blocked на инициацию? | **Да** (force in production settings + client guards) |
| Обход прямым API? | Нет при production settings |
| Webhook инициирует возврат? | **Нет** (только GET+local) |
| Webhook достаточно защищён? | GET обязателен; IP filter **нужно включить** на сервере |
| Что ещё перед запуском? | §22 checklist + live readiness docs |

---

## Изменённые файлы R38

- `backend/apps/payments/refund_policy.py` (new)
- `backend/apps/payments/services.py`
- `backend/apps/returns/services.py`, `views.py`
- `backend/integrations/yookassa/client.py`, `sber/client.py`
- `backend/config/settings/base.py`, `production.py`
- `backend/.env.example`, `../.env.production.example`, `docker-compose.prod.yml`
- `backend/tests/test_r38_refund_initiation_disabled.py` (new)
- `backend/tests/test_sber_payments.py`
- этот отчёт

**Стоп.** Commit / push / deploy не выполнялись.
