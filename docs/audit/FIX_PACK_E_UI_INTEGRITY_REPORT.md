# FIX-PACK E — UI Integrity, Dead Actions и корректная обработка ошибок

**Дата:** 2026-11-14  
**Среда:** локально `C:\ringoo`  
**Git branch / HEAD до работ:** `main` / `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8`  
**Production:** не затрагивался  
**Коммит / push:** не создавались  
**`.env` / секреты:** не читались  

---

## 1–3. Исходные описания из BLOCK 8

| ID | Severity | Формулировка | Файлы | Воспроизведение | Рекомендация аудитора |
|---|---|---|---|---|---|
| **B8-007** | High | Слабая обработка API 404 → длительный loading / `!data` | `admin/products\|users\|returns/[id]` | Битый deep-link | Явный `isError` → сообщение / notFound |
| **B8-008** | High | «Купить в 1 клик» — stub | `ProductPageClient.tsx` | Клик → «Отправить» закрывает modal | Скрыть или реализовать API |
| **B8-011** | Medium | Кнопка промо без onClick/API | `cart/page.tsx` | «Применить» | Подключить API или скрыть |
| **B8-012** | Medium | Ошибка загрузки корзины ≡ empty | `checkout/page.tsx` (и cart) | API cart down | Разделить error / empty |
| **B8-013** | Medium | 404 как generic error; dead support CTA | `orders/[id]/page.tsx` | Чужой/несуществующий id | notFound + рабочая ссылка |
| **B8-014** | Medium | Logout без invalidate cart | `useAuth.ts` | Logout | Invalidate cart keys |

Примечание: в §4.3 BLOCK 8 «Dead поддержка» ошибочно помечена как B8-014; в таблице дефектов поддержка входит в **B8-013**, logout — **B8-014**. Исправления следуют таблице.

---

## 4. READ-ONLY аудит (после Fix A–D)

| ID | Подтверждён? | Фактическая причина | Уже исправлен ранее? | Backend нужен? |
|---|---|---|---|---|
| B8-007 | **Да** | `if (isLoading \|\| !data)` **до** `isError` → при 404 spinner навсегда | Нет | Нет (только FE) |
| B8-008 | **Да** (Variant B) | Modal-заглушка; one-click order API отсутствует | Нет | Нет — не создаём новый процесс |
| B8-011 | **Да** (скрыть) | Кнопка без `onClick`; `POST /promocodes/validate/` есть, но `PROMOCODES_ENABLED` default off и **заказ не принимает promo** | Нет | Не в этом pack |
| B8-012 | **Да** на checkout; cart page уже разделял error | Checkout: `(isError \|\| empty)` одна ветка | Cart — да (частично) | Нет |
| B8-013 | **Да** | Generic «Не удалось загрузить»; Button поддержки без href | Нет | Нет |
| B8-014 | **Да** | `logout` чистил auth/me и staff-access, **не** `['cart']`; Fix C не закрывал | Нет | Нет |

### B8-008 — вывод

Полноценного «1 клик» endpoint / flow нет. **Variant B:** удалить CTA и modal.

### B8-011 — вывод

`PromoCodeValidateView` существует, но применение к cart/order не интегрировано. Клиентская скидка запрещена. **Скрыть UI**, не имитировать.

### B8-013 — поддержка

Подтверждённый контакт: `LEGAL_ORG.email` / `ORGANIZATION_CONTACT.email` (также в оферте). CTA → `mailto:` с subject номера заказа.

---

## 5. Таблица подтверждения / план

| ID | Подтверждён? | Причина | Файлы | Рекомендуемое исправление | Риск |
|---|---|---|---|---|---|
| B8-007 | Да | Spinner при `!data` после error | admin `products/users/returns/[id]` | `isError` first + `AdminQueryError` | Низкий |
| B8-008 | Да | Stub | `ProductPageClient.tsx` | Удалить кнопку/modal | Низкий |
| B8-011 | Да | Dead apply | `cart/page.tsx` | Убрать блок промо | Низкий |
| B8-012 | Да | Conflated states | `checkout/page.tsx` (+ retry cart) | Split error/empty | Низкий |
| B8-013 | Да | Generic + dead CTA | `orders/[id]/page.tsx` | 404/403 not-found UX; mailto | Низкий |
| B8-014 | Да | Stale cart cache | `useAuth.ts` | cancel/remove/invalidate `CART_QUERY_KEY` | Средний (guest cart race) |

**Вне scope / не трогали:** B8-009, B8-015–019, полный wiring promocodes, новый one-click backend.

---

## 6–9. Что исправлено / удалено / подключено

| Действие | Деталь |
|---|---|
| Исправлено | Admin 404/403/401/500 UI; checkout error≠empty; order not-found; logout cart |
| Удалено | «Купить в 1 клик» + modal; блок промокода в корзине |
| Подключено к существующему | Support → `mailto:LEGAL_ORG.email` (не выдуманный контакт) |
| Не подключено | Promocode validate/apply к заказу (неполон) |
| Backend | **не менялся** |

---

## 10–11. Изменения frontend / backend

### Frontend

| Файл | Изменение |
|---|---|
| `frontend/src/lib/errors.ts` | `getApiErrorStatus` |
| `frontend/src/components/admin/AdminQueryError.tsx` | **новый** — единый admin error UI |
| `frontend/src/app/admin/products/[id]/page.tsx` | error до loading; retry limits |
| `frontend/src/app/admin/users/[id]/page.tsx` | то же |
| `frontend/src/app/admin/returns/[id]/page.tsx` | то же |
| `frontend/src/app/products/[slug]/ProductPageClient.tsx` | убран 1-клик stub |
| `frontend/src/app/cart/page.tsx` | убран promo UI; retry на error |
| `frontend/src/app/checkout/page.tsx` | разделены error / empty |
| `frontend/src/app/orders/[id]/page.tsx` | not-found/403 UX; mailto support |
| `frontend/src/lib/hooks/useAuth.ts` | logout ↔ cart cache |
| Тесты | см. §15 |

### Backend

Нет изменений. Миграции не создавались.

---

## 12. Ошибки и empty states

| Поверхность | Loading | Empty | Error |
|---|---|---|---|
| Cart | skeleton | «Ваша корзина пуста» | friendly + Повторить |
| Checkout | Loading | «Корзина пуста» → каталог | friendly + Повторить / корзина |
| Admin detail | Loading | — | AdminQueryError (404/403/401/5xx) |
| Order detail | Loading | — | «Заказ не найден» для 404/403; retry для прочих |

---

## 13. Logout и cart cache

Порядок:

1. `cancelQueries(['cart'])` — in-flight user cart не запишет stale data  
2. `removeQueries(['cart'])` — убрать user cart из UI  
3. `logoutAuth()` (включая `invalidatePendingAuthRefresh` из Fix C)  
4. clear me / staff-access  
5. `invalidateQueries(['cart'])` — подтянуть **гостевую** корзину сессии  

Не делали `queryClient.clear()`.

---

## 14. Список изменённых файлов

- `frontend/src/lib/errors.ts`
- `frontend/src/lib/errors.api-status.test.ts` *(new)*
- `frontend/src/lib/hooks/useAuth.ts`
- `frontend/src/lib/hooks/useAuth.logout-cart.test.ts` *(new)*
- `frontend/src/components/admin/AdminQueryError.tsx` *(new)*
- `frontend/src/components/admin/AdminQueryError.test.tsx` *(new)*
- `frontend/src/app/admin/products/[id]/page.tsx`
- `frontend/src/app/admin/users/[id]/page.tsx`
- `frontend/src/app/admin/returns/[id]/page.tsx`
- `frontend/src/app/products/[slug]/ProductPageClient.tsx`
- `frontend/src/app/products/[slug]/one-click-removed.test.tsx` *(new)*
- `frontend/src/app/cart/page.tsx`
- `frontend/src/app/cart/page.promo.test.tsx` *(new)*
- `frontend/src/app/checkout/page.tsx`
- `frontend/src/app/checkout/checkout-cart-states.test.tsx` *(new)*
- `frontend/src/app/orders/[id]/page.tsx`
- `frontend/src/app/orders/[id]/order-detail-states.test.tsx` *(new)*
- `docs/audit/FIX_PACK_E_UI_INTEGRITY_REPORT.md` *(this)*

---

## 15. Результаты тестирования

### Frontend

| Check | Result |
|---|---|
| Vitest Fix E + cart + Fix C/D related (11 files, 27 tests) | **passed** |
| `tsc --noEmit` | **OK** |
| ESLint изменённых файлов без pre-existing warnings | **OK** |
| Pre-existing warnings | `useAuth` setState-in-effect; `ProductPageClient` set-state-in-effect; admin products `window.location.href` — не регрессия E |
| `npm run build` | **OK** (exit 0) |

### Backend

| Check | Result |
|---|---|
| `manage.py check` | OK |
| Fix A + B + SEC-006 + SEC-005 (36 tests) | **passed** |
| `makemigrations` | не требовался (backend не менялся) |

---

## 16. Регрессия FIX-PACK A/B/C/D

| Pack | Проверка | Статус |
|---|---|---|
| A | `test_fix_pack_a_guest_success`, checkout-success-path | OK |
| B | `test_fix_pack_b_order_cancellation` | OK |
| C | `auth-refresh.test.ts`; logout по-прежнему вызывает `logoutAuth` → invalidate refresh | OK |
| D | `checkout-idempotency.test.ts`, sec005 | OK |

---

## 17. Регрессия BLOCK 1–7

Точечно не перегонялись полные onec suites в этом pack (код склад/1С/резервов не менялся). Релевантные order/guest suites — зелёные. Postgres load / browser E2E — **не** запускались.

---

## 18. Непроверенные сценарии

1. Ручной browser QA admin deep-link 404.  
2. Визуальная проверка PDP mobile после удаления 1-клик (mobile bottom bar и так без 1-клик).  
3. Полный E2E logout → header badge guest cart.  
4. Включение `PROMOCODES_ENABLED` + wiring к заказу — продуктовая задача вне E.

---

## 19. Дефекты BLOCK 8 вне scope

B8-009 (AdminGuard middleware), B8-015 (docs drift), B8-016 (sitemap), B8-017 (release), B8-018 (perf), B8-019 (responsive) — **не** исправлялись.

---

## 20. Production

Production не открывался и не изменялся. Только локальный `C:\ringoo`.

---

## Критерии приёмки (самооценка)

| Критерий | Статус |
|---|---|
| Admin 404/403/401/500 без eternal loading | Готов |
| 1-клик не вводит в заблуждение | Удалён |
| Промо не изображается работающим | Убран UI |
| Cart load error ≠ empty | Cart был OK; checkout разделён |
| Order not-found / support | Готов |
| Logout не показывает user cart | cancel/remove/invalidate |
| A/B/C/D без регрессии в прогнанных suites | OK |
| Отчёт | Этот файл |

**Стоп:** Fix-pack E завершён. Следующий pack не начинался.
