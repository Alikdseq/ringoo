# FIX-PACK A — гостевой success после cash/COD (B8-001 + B8-003)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Production:** не затрагивался  
**Коммит:** не создавался  

---

## 1. Первопричина

### B8-001 (Critical)

После guest checkout с `payment_type` ∈ {`cash`, `card_on_delivery`} фронт делал:

`router.push(/orders/${order.id}/success)` → страница вызывала `getOrder(id)` → `GET /api/v1/orders/{id}/` с `permission_classes = [IsAuthenticated]`.

У гостя нет JWT → ошибка загрузки. Публичная `/orders/success?order_number=` уже существовала и **не** ходила в auth-only API, но checkout на неё не вёл. Для online путь уже stash’ил `guest_access_token` через `stashPayAuth`; для cash/COD токен после create не сохранялся.

### B8-003 (High)

`orders/[id]/success/page.tsx` брал `params` из props. Соседние страницы (`payment/return`, `payment/fail`, `orders/[id]`) используют `useParams()` (Next.js 16.4). Риск пустого/устаревшего `id` на client page.

---

## 2. Старый flow

```
Guest cash/COD
  POST /orders/ → 201 + guest_access_token (только в теле)
  → /orders/{id}/success
  → getOrder(id)   # auth-only
  → ошибка «Не удалось загрузить данные заказа»

Auth cash/COD
  → /orders/{id}/success → getOrder OK

Guest online
  → stashPayAuth + redirect PSP (без изменений в этом pack)
```

---

## 3. Новый flow

```
Guest cash/COD
  POST /orders/ → 201 + guest_access_token
  → stashPayAuth(orderId, { phone, order_number, guest_token })  # sessionStorage, не URL
  → /orders/success?order_number=…   # только номер; без PII API
  → «Проверить статус» → /order-status (phone + guest_token из stash)

Auth cash/COD
  → /orders/{id}/success
  → useParams().id + getOrder (как раньше по смыслу)

Guest accidental /orders/{id}/success
  → getOrder НЕ вызывается
  → если есть stash → replace на /orders/success?order_number=
  → иначе безопасное сообщение + ссылки

Online payment flow
  без изменений (redirectUrl / fail path)
```

Повторное открытие success **не** создаёт заказ (только чтение UI / optional redirect).

---

## 4. Изменённые файлы

| Файл | Изменение |
|---|---|
| `frontend/src/lib/orders/checkout-success-path.ts` | **новый** — выбор URL success |
| `frontend/src/lib/orders/checkout-success-path.test.ts` | **новый** |
| `frontend/src/app/checkout/page.tsx` | stash guest token + guest/auth redirect |
| `frontend/src/app/orders/[id]/success/page.tsx` | `useParams` + guest guard без `getOrder` |
| `frontend/src/app/orders/[id]/success/page.test.tsx` | обновлён |
| `frontend/src/app/orders/success/page.test.tsx` | **новый** |
| `backend/tests/test_fix_pack_a_guest_success.py` | **новый** — контракт guest/API |
| `docs/audit/FIX_PACK_A_GUEST_SUCCESS_REPORT.md` | этот отчёт |

Backend views/FSM/резервы **не менялись**.

---

## 5. Backend и frontend

- **Backend:** без изменений кода. Контракт подтверждён тестами: guest create → token; anon detail → 401; track без token → без ПДн; track с token → полный заказ.
- **Frontend:** redirect + sessionStorage + `useParams` + защита `[id]/success`.

---

## 6. Защита guest access

| Правило | Как соблюдено |
|---|---|
| Не auth-only `getOrder` для гостя | Guest → `/orders/success`; `[id]/success` не зовёт `getOrder` без auth |
| Токен не в публичном URL | Только `order_number` в query; token в `sessionStorage` через `stashPayAuth` |
| `order_number` ≠ авторизация | Публичная success показывает только номер; ПДн — через `/order-status` + `guest_token` (SEC-006) |
| Неверный/отсутствующий token | Track без/с wrong token → `guest_token_required`, без `full_name`/`items` |
| Не второй механизм доступа | Используются существующие `issue_guest_access_token` / track / `stashPayAuth` |

---

## 7. Результаты тестов

| Проверка | Результат |
|---|---|
| `tests/test_fix_pack_a_guest_success.py` (cash, COD, wrong token) | **3 passed** |
| `apps/orders/tests.py` | **31 passed** |
| `tests/test_sec006_guest_access_token.py` | 14 passed, **1 failed** (`test_valid_token_can_cancel`: expect `cancelled`, got `closed`) — **B8-010 / Fix-pack B**, не регрессия A; отмена по API 200, меняется только assert статуса |
| Vitest: checkout-success-path, `[id]/success`, `/orders/success`, checkout, payment/return | **12 passed** |
| BLOCK 3 series/cart + BLOCK 4 orders/locks | **28 passed** (вместе с Fix-pack A) |

Сценарии покрытия Fix-pack A:

1. Guest cash create + token + detail 401 + track limited/full — да  
2. Guest COD (`card_on_delivery`) — да  
3. Success path без auth-only для гостя — да (unit + page)  
4. Guest без getOrder на `[id]/success` — да  
5. Wrong token без ПДн — да  
6. Auth success + getOrder — да  
7. Payment return тесты — да (не сломаны)  
8. `useParams` — да (mock + реализация)

---

## 8. TypeScript / ESLint / build

| Проверка | Результат |
|---|---|
| `tsc --noEmit -p tsconfig.typecheck.json` | **OK** (exit 0) |
| ESLint изменённых файлов | **0 errors**, 4 warnings (только pre-existing в `checkout/page.tsx`: setState-in-effect / object-injection) |
| `npm run build` | **OK** (exit 0) |

---

## 9. Регрессии BLOCK 1–7

- BLOCK 3 / 4 (серии, корзина, locks/orders): **зелёные**.  
- Резервы / FSM / 1С APPLY / платежный create+webhook: **код не менялся**.  
- Online checkout path (`redirectUrl` / `stashPayAuth` для pay): **сохранён**.

---

## 10. Оставшиеся проблемы

- **B8-010** — устаревшие asserts `status == cancelled` (в т.ч. SEC-006 cancel) → Fix-pack B.  
- Публичная success показывает только номер (без состава) — осознанно; полные данные через `/order-status` + token.  
- B8-002 / B8-004 / … — вне scope Fix-pack A.

---

## 11. Production

- Production не трогался.  
- APPLY 1С / migrate / restart / `.env` / реальные платежи / коммит — **не выполнялись**.

---

**Fix-pack A завершён.** Fix-pack B не начат.
