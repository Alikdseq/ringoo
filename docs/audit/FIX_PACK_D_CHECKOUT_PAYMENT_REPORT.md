# FIX-PACK D — Checkout / Payment Hardening (B8-004, B8-005)

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production:** не затрагивался  
**Коммит / push:** не создавались  
**Реальные платежи:** не выполнялись  
**`.env` / секреты:** не читались и не менялись  

---

## 1–2. Исходные описания из BLOCK 8

| ID | Severity | Формулировка | Файлы (аудит) | Воспроизведение | Влияние | Рекомендация аудитора |
|---|---|---|---|---|---|---|
| **B8-004** | High | Checkout создаёт новый idempotency key на каждый submit | `checkout/page.tsx` | Двойной / тройной клик, повтор после timeout | Риск дублей заказов при гонке | Стабильный key на попытку + disable submit + серверный claim |
| **B8-005** | High | Гостевой pay зависит от `guest_token` в `sessionStorage` | `payments.service.ts`, return/fail | Новый браузер / очистка stash / reload без stash | 403 на status/retry | Persist + recover UI; не ослаблять SEC-006 |

Сверка после Fix-pack A/B/C: оба дефекта **подтверждены** в коде working tree до правок этого pack. JWT refresh (C) и FSM cancel (B) к причинам не относились.

---

## 3. READ-ONLY аудит

### B8-004 — idempotency checkout

**Frontend (до фикса):**
- Ключ генерировался внутри submit (`crypto.randomUUID()` на каждый вызов) → повтор клика / retry после timeout = **новый** `X-Idempotency-Key`.
- `createOrderMutation.isPending` блокировал кнопку (`checkoutBusy`), но это **не** защищает от: второго запроса до установки pending, повторной вкладки, сетевого retry с новым ключом.
- Корзина инвалидировалась только после успеха / redirect — это сохранено.

**Backend (до фикса):**
- `OrderListCreateView.post` читал `X-Idempotency-Key`, scope `user` / `guest session` (`_order_idempotency_cache_key`).
- Кэш **записывался только после** успешного `201` → два параллельных запроса с одним ключом оба проходили `cache.get is None` и создавали **два заказа**.
- Повтор с тем же ключом после успеха возвращал закэшированный ответ (один заказ) — OK для последовательного retry.
- Валидация / stock error: ключ не оставался «залипшим» (delete) — после фикса pending claim тоже снимается при 400.

**Фактический контракт backend до фикса:** идемпотентность **после** создания; **не** атомарный claim на время создания → гонка параллельных запросов.

### B8-005 — guest payment access

**Поток:**
1. Guest create order → `guest_access_token` только в теле `201` (SEC-006).
2. Checkout `stashPayAuth(orderId, { phone, order_number, guest_token })` → `sessionStorage` (не URL).
3. Redirect ЮKassa / Сбер → return/fail читают `takePayAuth(orderId)`.
4. Status/pay API принимают guest через body/header с `guest_token` (+ phone/order_number), не через `order_number` alone.
5. Восстановление в другом браузере: `/order-status` + email recover → `stashGuestTokenByOrderNumber` (уже существовало, Fix A).

**Проблемы (до фикса):**
- Return page при пустом stash всё равно дергала payment status → 403 / плохой UX.
- Fail retry без токена пытался pay без ясного сообщения.
- `takePayAuth` не подтягивал отдельно сохранённый token по `order_number` (cash/COD / recover path).
- Новая вкладка / другой браузер / очищенный sessionStorage → нет токена; **это ожидаемо при SEC-006**, если нет recover.

**Хранение:** оставлено `sessionStorage` (не `localStorage`, не HttpOnly cookie в этом pack). Обоснование: XSS-риск localStorage выше при длинном TTL; cookie потребовала бы backend Set-Cookie на create + SameSite политика для PSP return; существующий recover flow уже закрывает «новый браузер» без ослабления IDOR.

---

## 4. Подтверждение дефектов

| ID | Подтверждён? | Текущая причина | Файлы | Минимальное исправление | Риск |
|---|---|---|---|---|---|
| B8-004 | **Да** | FE: новый UUID каждый submit; BE: нет pending claim → parallel race | `checkout/page.tsx`, `checkout-idempotency.ts`, `orders/views.py` | Stable key + fingerprint; `cache.add(pending)`; 409 in progress; release on validation fail | Средний (cache backend must support atomic add) |
| B8-005 | **Да** (частично UX + merge) | Return/fail без stash → 403; token merge по order_number отсутствовал | `payments.service.ts`, return/fail pages | Не бить API без token; UI → order-status; merge peek by order_number; fail retry guard | Низкий при сохранении SEC-006 |

**Не «чинилось» ослаблением безопасности:** доступ по одному `order_number` не добавлялся; токен не в URL; JWT ≠ guest token.

---

## 5. Контракт A — idempotency checkout

### До

| Аспект | Поведение |
|---|---|
| Где ключ | Новый UUID на каждый submit handler |
| TTL | Backend cache ~86400s после успеха |
| Логическая попытка | Не определена |
| FE retry | Новый ключ → риск второго заказа |
| BE повтор | После успеха — cached response; **во время** create — дубль |
| Тот же ключ / другой payload | Возврат первого ответа (после успеха) |
| Параллель | Два заказа возможны |
| Новый ключ | Каждый клик |

### После

| Аспект | Поведение |
|---|---|
| Где ключ | `resolveCheckoutIdempotencyKey` + refs на checkout page |
| TTL FE | Пока fingerprint тот же и нет успеха; refs сбрасываются после success/redirect |
| Логическая попытка | Fingerprint: cartId, payment, store, delivery, phone, name, items, acceptPriceChanges |
| FE retry / double-click | Тот же key; кнопка `checkoutBusy` |
| BE повтор (тот же key, успех уже есть) | Cached `201` + тот же order id |
| BE параллель (pending) | `409` `idempotency_in_progress` |
| Claim | `cache.add({pending:True})` до create; `cache.set(data)` после; `cache.delete` на validation/stock |
| Тот же ключ / другой payload (после успеха) | Безопасно: возвращается **первый** закэшированный ответ (дубля нет). FE при смене fingerprint выдаёт **новый** ключ → новый заказ осознанно |
| Новый ключ | Смена fingerprint **или** после успешного оформления |

**Ограничение:** если cache backend не атомарный между воркерами (маловероятно для Redis; LocMem — per-process), межпроцессная гонка теоретически возможна. Тесты используют LocMem в одном процессе.

**Одного disabled submit недостаточно** — серверный pending claim обязателен; он добавлен.

---

## 6. Контракт B — guest payment access

### До

- Токен в `sessionStorage` под `ringoo_pay_auth:{orderId}`.
- Return всегда query payment → 403 без stash.
- Recover существовал на `/order-status`, но return UI на него не направлял явно при missing stash.

### После

| Аспект | Поведение |
|---|---|
| Получение доступа | Create order → `guest_access_token` в теле; stash в sessionStorage |
| Хранение | `sessionStorage` (`ringoo_pay_auth` + `ringoo_guest_token_by_order:{order_number}`) |
| Payment return | `takePayAuth` (без consume) + merge token by order_number; poll только если JWT **или** guest_token |
| Reload той же вкладки | Stash жив → status OK |
| Нет stash | UI «Нужен доступ» → `/order-status` (order_number только как hint в query, **не** auth) |
| Новый браузер | Только recover (email) / повторный login владельца — **не** order_number alone |
| Fail retry | Guest без token — понятная ошибка, без pay API |
| IDOR / SEC-006 | Без валидного guest_token персональные данные не отдаются |
| JWT vs guest | Не взаимозаменяемы |

**Ограничение (зафиксировано):** безопасное восстановление в новом браузере **без** дополнительной идентификации (email recover / аккаунт) невозможно и **не** реализовывалось через `order_number`.

---

## 7. Изменения frontend

| Файл | Суть |
|---|---|
| `frontend/src/lib/orders/checkout-idempotency.ts` | **новый** — fingerprint + stable key |
| `frontend/src/lib/orders/checkout-idempotency.test.ts` | **новый** |
| `frontend/src/app/checkout/page.tsx` | refs + resolve key; clear после успеха; submit disabled через `checkoutBusy` |
| `frontend/src/lib/api/services/payments.service.ts` | dual stash; `takePayAuth` merge by order_number; reload-safe (no consume) |
| `frontend/src/lib/api/services/payments.stash.test.ts` | **новый** |
| `frontend/src/app/orders/[id]/payment/return/page.tsx` | gate без API при missing guest; useSyncExternalStore; link order-status |
| `frontend/src/app/orders/[id]/payment/return/page.test.tsx` | сценарии B8-005 |
| `frontend/src/app/orders/[id]/payment/fail/page.tsx` | guest retry только с полным auth; сообщение о recover |

Корзина: не очищается до подтверждённого create; при network/unknown result ключ **сохраняется** (refs не сбрасываются) → retry не плодит заказ; invalidate cart только после success/redirect как раньше.

---

## 8. Изменения backend

| Файл | Суть |
|---|---|
| `backend/apps/orders/views.py` | pending `cache.add`; 409 `idempotency_in_progress`; delete pending на empty cart / validation / stock |
| `backend/tests/test_sec005_order_idempotency.py` | validation releases lock; parallel pending → 409 |

Миграции не добавлялись. FSM / cancel (Fix B), JWT refresh (Fix C), 1С — не менялись.

---

## 9. Хранение и восстановление guest token

- **Не** переносили в `localStorage`.
- **Не** клали в URL / redirect query.
- **Не** вводили HttpOnly cookie в этом pack (потребует отдельный backend+PSP SameSite план).
- Dual key в sessionStorage: by order id + by order_number (для merge после Fix A cash path / recover).
- Recover: существующий `/orders/guest-access/recover/` (+ confirm) — без изменений контракта SEC-006.

---

## 10. Двойной submit и timeout

| Сценарий | Результат после фикса |
|---|---|
| Одинарный submit | 1 заказ |
| Двойной/тройной клик (тот же fingerprint) | Тот же key; FE busy; BE → 1 заказ или 409→retry→cached |
| Медленный backend | Pending claim блокирует параллель |
| Timeout после фактического create | Повтор с тем же key → cached 201, тот же id |
| Validation 400 | Pending снят → можно исправить и повторить тем же/новым key |
| Смена корзины/оплаты | Новый fingerprint → новый key → новый заказ (осознанно) |
| Успех | Refs cleared → следующий checkout — новый key |

---

## 11. Payment return / reload / retry

| Сценарий | Результат |
|---|---|
| Guest online → PSP → return (та же вкладка) | Stash → poll status |
| Reload return | Stash жив (take не consume) → OK |
| Fail → «Оплатить снова» со stash | initiate pay с guest_token |
| Fail без stash | Сообщение + order-status, без pay |
| Return без stash | «Нужен доступ», API не вызывается |
| Чужой order_number без token | Нет PII (SEC-006) |
| Auth user без stash | JWT path, poll OK |

---

## 12. Безопасность и SEC-006

- Токен не в query return/fail URL.
- `order_number` в `/order-status?order_number=` — только UX hint, не авторизация.
- Guest token не участвует в JWT refresh (Fix C).
- JWT не заменяет guest token для чужого гостевого заказа.
- SEC-006 suite: **16 passed**.
- Повторная оплата оплаченного заказа — по-прежнему на backend payment rules (не ослаблялись); UI fail/return не форсирует pay при paid.

---

## 13. Список изменённых файлов (этот pack)

**Backend**
- `backend/apps/orders/views.py`
- `backend/tests/test_sec005_order_idempotency.py`

**Frontend**
- `frontend/src/lib/orders/checkout-idempotency.ts` *(new)*
- `frontend/src/lib/orders/checkout-idempotency.test.ts` *(new)*
- `frontend/src/app/checkout/page.tsx`
- `frontend/src/lib/api/services/payments.service.ts`
- `frontend/src/lib/api/services/payments.stash.test.ts` *(new)*
- `frontend/src/app/orders/[id]/payment/return/page.tsx`
- `frontend/src/app/orders/[id]/payment/return/page.test.tsx`
- `frontend/src/app/orders/[id]/payment/fail/page.tsx`

**Docs**
- `docs/audit/FIX_PACK_D_CHECKOUT_PAYMENT_REPORT.md` *(this file)*

---

## 14. Запущенные тесты и результаты

### Backend

| Suite | Result |
|---|---|
| `tests/test_sec005_order_idempotency.py` | **8 passed** |
| `tests/test_fix_pack_a_guest_success.py` | **3 passed** |
| `tests/test_fix_pack_b_order_cancellation.py` | **9 passed** |
| `tests/test_sec006_guest_access_token.py` | **16 passed** |
| `tests/test_yookassa_payments.py` | **16 passed** |
| `tests/test_payment_security.py` | **30 passed** |
| `tests/test_func002_func009_cancel_policy.py` | **7 passed** |
| `tests/test_sec003_cancel_releases_stock.py` | **6 passed** |
| `tests/test_onec_block4_orders_locks.py` | **8 passed** |
| `tests/test_onec_block3_series_cart.py` + block5 + stock idempotency | **46 passed** |
| `manage.py check` | OK (0 issues) |
| `makemigrations --check --dry-run` | No changes detected |

### Frontend

| Check | Result |
|---|---|
| Vitest: checkout-idempotency, payments.stash, payment return, checkout-success-path, auth-refresh, success pages | **все passed** (в т.ч. 19 + 13 в двух прогонах) |
| `tsc --noEmit` | OK |
| ESLint (файлы Fix D кроме checkout pre-existing warnings) | **0 errors / 0 warnings** |
| ESLint `checkout/page.tsx` | pre-existing `react-hooks/set-state-in-effect` (store stock effect) — **не регрессия этого pack** |
| `npm run build` | **OK** (exit 0) |

---

## 15. Регрессия FIX-PACK A/B/C

| Pack | Проверка | Статус |
|---|---|---|
| A | `test_fix_pack_a_guest_success`, checkout-success-path, success page tests | OK |
| B | `test_fix_pack_b_order_cancellation`, sec003, func002/009 | OK |
| C | `auth-refresh.test.ts` | OK |

---

## 16. Регрессия BLOCK 1–7

- BLOCK 3 series/cart, BLOCK 4 locks, BLOCK 5 security integrity, stock idempotency — **passed**.
- Полный `pytest` всего репозитория и Postgres 50k load (B8-018) — **не** гонялись в этом pack.
- Real YooKassa E2E / production webhook — **не** выполнялись (ограничение §1).

---

## 17. Непроверенные сценарии и ограничения

1. E2E браузерный round-trip ЮKassa sandbox (реальные redirect).
2. Межворкерная гонка idempotency при не-Redis cache (теоретически).
3. Private / blocked `sessionStorage` (Safari ITP edge) — recover path остаётся единственным.
4. Same key + **другой** payload после успеха: BE отдаёт первый cached response (не 422 conflict). Защита от «тихой» подмены состава — на FE fingerprint (новый key). Усиление BE payload-hash — вне минимального фикса.
5. Новая вкладка без stash: требует recover — by design.

---

## 18. Нерешённые дефекты BLOCK 8 вне scope

B8-007, B8-008, B8-011, B8-012…B8-019, B8-017 (release hygiene) — **не** трогались. Следующий по плану аудита: **Fix-pack E** (dead UI) — **не начинался**.

---

## 19. Production

Production не открывался, APPLY/migrate/restart/deploy не выполнялись. Изменения только в локальном `C:\ringoo`.

---

## Критерии приёмки (самооценка)

| Критерий | Статус |
|---|---|
| B8-004: один логический checkout → не несколько заказов при double/parallel/timeout retry | **Готов к приёмке** (unit/API) |
| B8-005: предсказуемый безопасный доступ после return/reload в рамках sessionStorage + recover | **Готов к приёмке** |
| order_number ≠ auth | OK |
| guest token не в URL | OK |
| SEC-006 не ослаблен | OK |
| Корзина не чистится ошибочно | OK (контракт сохранён) |
| Fix A/B/C без регрессии в прогнанных suites | OK |

**Стоп:** Fix-pack D завершён. Следующий pack не начинался.
