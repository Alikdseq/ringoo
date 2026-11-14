# RELEASE 2 — Точный манифест Git-коммитов Ringoo

**Дата:** 2026-11-14  
**Режим:** READ-ONLY  
**Проект:** `C:\ringoo`  
**Git write / migrate / code edit / production:** не выполнялись  

Основан на **свежем** `git status` (не копия RELEASE 1).  
После создания этого файла в working tree появится ещё один `??` путь — он включён в Commit 8 как Documentation.

---

## 1. Git-состояние (актуально)

| Поле | Значение |
|---|---|
| Branch | `main` |
| HEAD | `b3a9db433a533cdc9254ddb4f2a189ee41a27ef8` |
| Modified (`M`) | **76** |
| Untracked (`??`) | **69** (+ этот манифест после записи = **70**) |
| Status lines (до записи манифеста) | **145** |
| Deleted / Renamed / Conflicts | **0 / 0 / нет** |

Дельта к RELEASE 1 (144 строки): +1 untracked `docs/audit/RELEASE_1_FINAL_INVENTORY.md`.

---

## 2. Проверенная последовательность миграций

| Migration | В Git HEAD? | Working tree | dependencies | operations | Reverse |
|---|---|---|---|---|---|
| `products.0009_block10_state_sync` | **Да (tracked)** | без локальных правок | `products.0008` | `AlterField` ProductImage.image | авто Django |
| `stores.0008_map_confirmed_onec_warehouses` | **Нет** | `??` | `stores.0007` | `RunPython(apply_mapping, reverse_mapping)` | **есть** `reverse_mapping`: сброс onec_* / удаление только созданного tech-sklad |
| `stores.0009_stock_product_protect` | **Нет** | `??` | `stores.0008` **и** `products.0009` | `AlterField` Stock.product → `PROTECT` | авто Django |

**Порядок apply на целевой БД:**

1. Убедиться: `products.0009` и `stores.0007` уже applied.  
2. `stores.0008`  
3. `stores.0009`

**Замечания:**

- `0008` **не читает** `docs/integrations/onec_warehouse_mapping.json` — UUID зашиты в `CONFIRMED` внутри миграции.  
- JSON + `warehouse_map.py` всё равно **Required** как единый ops/runtime источник правды рядом с миграцией (Commit 1).  
- `0008` зависит от существующих Store по **slug**; риск неверного slug на prod — ops.  
- Ничего не применялось.

---

## 3. `git diff --check` (whitespace)

```
docs/API.md:258: trailing whitespace.
docs/API.md:259: trailing whitespace.
```

Фактически строки с хвостовыми пробелами (markdown hard-break `  `):

| Строка | Минимальное исправление (отдельным шагом, не сейчас) |
|---|---|
| 257 | Убрать два пробела в конце `**Дата создания:** …` **или** оставить осознанный hard-break |
| 258 | То же для `**Обновлено:** …` |
| 259 | То же для `**Версия:** 1.1` |

**Не исправлялось** в RELEASE 2.

---

## 4. Исключения (Exclude)

| Path | Git | Reason |
|---|---|---|
| `промпт.txt` | M | Локальный операторский промпт |
| `Описание работ.txt` | ?? | Внешний текст объёма работ |
| `docs/Инструкция_API_1С_для_разработчиков_сайта.docx` | ?? | Бинарный коммерческий/внешний документ |
| `docs/Интеграция с 1С — объём работ.docx` | ?? | То же |
| `docs/Онлайн-оплата — объём работ.docx` | ?? | То же |
| `docs/Отчёт_интеграции_Ringo_1С_Сбер_касса.docx` | ?? | То же |
| `frontend/AGENTS.md` | ?? | Локальные AI-инструкции FE, не runtime |
| `backend/var/` (results/fixtures B8-018) | ignored | Генерируемые артефакты (`gitignore: var/`) |

Ничего не удалялось.

---

## 5. Пересечения и принятые решения

| Файл | Конфликт | Решение |
|---|---|---|
| `backend/apps/orders/views.py` | мог быть FSM+checkout | Diff = **только** idempotency pending → **Commit 3** |
| `backend/apps/orders/serializers.py` + `orders/tests.py` | warehouse pickup | Diff = `is_warehouse` не блокирует заказ → **Commit 1** |
| `backend/apps/orders/services/transitions.py` | FSM | **Commit 2** |
| `backend/apps/admin_api/views/orders.py` | admin FSM aliases | **Commit 2** |
| `backend/apps/cart/*` | series vs checkout | Diff = stock prefetch / availability → **Commit 1** |
| `backend/apps/users/tests.py` | G vs auth | Stock fixture для JWT merge cart → **Commit 4** |
| `frontend/.../checkout/page.tsx` | Fix D + L sticky | Не дробим → **Commit 3** (checkout) |
| `frontend/.../errors.ts` | E/F shared helper | `getApiErrorStatus` → **Commit 5** |
| `frontend/.../auth.service.ts` | C + staff | Cookies + staff fetch в одном файле → **Commit 4**; staff tests → **Commit 5** |
| `frontend/.../types/api.ts` | `is_warehouse` | **Commit 6** (витрина/StoreSelector) |
| `frontend/.../useAuth.ts` | C + E logout | Целиком **Commit 4** |

Дробление файлов **не делалось**.

---

## 6. Итоговый порядок коммитов

| # | Title | #files | Migrations | Depends on | Risk |
|---|---|---:|---|---|---|
| **1** | `feat(onec): stock snapshot, warehouse map, catalog guards` | 42 | stores.0008, stores.0009 | — | High (data mig 0008, PROTECT) |
| **2** | `feat(orders): FSM v2 transitions and cancel integrity` | 12 | — | 1 (stock release) | Medium |
| **3** | `fix(checkout): idempotency, guest success, pay stash` | 19 | — | 2 recommended | High (commerce) |
| **4** | `fix(auth): cookie refresh and logout cart sync` | 9 | — | — | Medium |
| **5** | `fix(admin): AdminGuard and admin query error UX` | 11 | — | 4 (auth cookies) | Medium |
| **6** | `fix(ui): storefront integrity and mobile responsive` | 15 | — | 3 optional | Low–Medium |
| **7** | `fix(seo): shared public routes for sitemap` | 5 | — | — | Low |
| **8** | `docs: API sync and audit reports BLOCK/Fix/Release` | 23 | — | after 1–7 preferred | Low (trailing ws) |
| **9** | `chore: add OneC load-test benchmark scripts` | 3 | — | 1 | Low (tooling) |

**Exclude из status:** 7 путей (§4; `backend/var/` не в status — already ignored).

Включаемые: 42+12+19+9+11+15+5+23+3 = **139**.  
Status до записи манифеста 145 − 7 exclude = 138; + этот файл в Commit 8 уже учтён в 23 → после появления `RELEASE_2` на диске status станет 146, покрытие 139+7=146.

---

## 7. Полный пофайловый реестр

Легенда Category: Runtime / Migration / Test / Documentation / Tooling / Exclude.  
Commit: 1–9 или `EX`.

### Commit 1 — OneC / stock / warehouses (42)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| backend/integrations/onec/catalog_sync.py | M | Runtime | B1–7 | 1 | Да | Redis lock, SyncLog | APPLY lock / sync orchestration |
| backend/integrations/onec/importer.py | M | Runtime | B1–7 | 1 | Да | parser, stock_ops | plan + apply catalog |
| backend/integrations/onec/parser.py | M | Runtime | B1–7 | 1 | Да | — | XML DOM parse |
| backend/integrations/onec/orders.py | M | Runtime | B1–7 | 1 | Да | FSM/orders | 1С order sync |
| backend/integrations/onec/reporting.py | ?? | Runtime | B7 | 1 | Да | importer issues | fail-closed reporting |
| backend/integrations/onec/warehouse_map.py | ?? | Runtime | B2 | 1 | Да | mapping JSON | confirmed warehouses |
| docs/integrations/onec_warehouse_mapping.json | ?? | Runtime | B2 | 1 | Да | 0008/ops | warehouse truth companion |
| backend/apps/stores/migrations/0008_map_confirmed_onec_warehouses.py | ?? | Migration | B2/B5 | 1 | Да | stores.0007 | data map warehouses |
| backend/apps/stores/migrations/0009_stock_product_protect.py | ?? | Migration | B5 | 1 | Да | stores.0008, products.0009 | PROTECT Stock.product |
| backend/apps/stores/stock_ops.py | M | Runtime | B1–5 | 1 | Да | StockMovement | batch upsert/idempotency |
| backend/apps/stores/models.py | M | Runtime | B1–5 | 1 | Да | 0009 | stock/series fields |
| backend/apps/stores/serializers.py | M | Runtime | B3–5 | 1 | Да | models | API stock shape |
| backend/apps/stores/views.py | M | Runtime | B3–5 | 1 | Да | stock_ops | public/admin stock |
| backend/apps/stores/admin.py | M | Runtime | B5 | 1 | Да | models | admin stock safety |
| backend/apps/stores/tests.py | M | Test | B1–5 | 1 | Да | stock_ops | store/stock regression |
| backend/apps/products/services/lifecycle.py | ?? | Runtime | B5 | 1 | Да | Stock | archive vs delete |
| backend/apps/products/admin.py | M | Runtime | B5 | 1 | Да | lifecycle | admin product lifecycle |
| backend/apps/products/catalog_filters.py | M | Runtime | B5–6 | 1 | Да | — | catalog filters |
| backend/apps/products/serializers.py | M | Runtime | B3–6 | 1 | Да | stock | availability |
| backend/apps/products/views.py | M | Runtime | B5–6 | 1 | Да | serializers | catalog API |
| backend/apps/products/services/product_images.py | M | Runtime | B5–6 | 1 | Да | — | images pipeline |
| backend/apps/products/management/commands/import_onec_catalog.py | M | Runtime | B1–7 | 1 | Да | importer | CLI import |
| backend/apps/products/management/commands/diagnose_onec_stock_series.py | M | Runtime | B3 | 1 | Да | stock | series diagnose |
| backend/apps/admin_api/views/products.py | M | Runtime | B5 | 1 | Да | lifecycle | safe delete API |
| backend/apps/admin_api/views/stock.py | M | Runtime | B5 | 1 | Да | stock_ops | admin stock |
| backend/apps/cart/views.py | M | Runtime | B3 | 1 | Да | Stock prefetch | retail availability |
| backend/apps/cart/serializers.py | M | Runtime | B3 | 1 | Да | Store | inactive store guard |
| backend/apps/cart/tests.py | M | Test | B3 | 1 | Да | cart views | cart/stock tests |
| backend/apps/orders/serializers.py | M | Runtime | B2/B5 | 1 | Да | Store.is_warehouse | pickup warehouse allowed |
| backend/apps/orders/tests.py | M | Test | B2/B5 | 1 | Да | serializers | warehouse pickup test |
| backend/tests/onec_test_utils.py | ?? | Test | B1–7 | 1 | Да | warehouse_map | shared fixtures |
| backend/tests/test_onec_stock_idempotency.py | ?? | Test | B1 | 1 | Да | stock_ops | |
| backend/tests/test_onec_stock_reconciliation.py | ?? | Test | B2 | 1 | Да | stock_ops | |
| backend/tests/test_onec_block3_series_cart.py | ?? | Test | B3 | 1 | Да | cart/stock | |
| backend/tests/test_onec_block4_orders_locks.py | ?? | Test | B4 | 1 | Да | catalog_sync | |
| backend/tests/test_onec_block5_security_integrity.py | ?? | Test | B5 | 1 | Да | lifecycle/0009 | |
| backend/tests/test_onec_block6_performance.py | ?? | Test | B6 | 1 | Да | batch upsert | |
| backend/tests/test_onec_block7_reporting_guards.py | ?? | Test | B7 | 1 | Да | reporting | |
| backend/tests/test_onec_http.py | M | Test | B1–7 | 1 | Да | onec client | |
| backend/tests/test_block8_catalog_guards.py | M | Test | B8/B5 | 1 | Да | catalog | |
| backend/tests/test_int009_stock_ledger_complete.py | M | Test | B1 | 1 | Да | stock_ops | |
| backend/tests/test_admin_integrity.py | M | Test | B5 | 1 | Да | admin products | |

**Count Commit 1:** 42 (см. §8).

### Commit 2 — FSM v2 (12)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| backend/apps/orders/services/transitions.py | M | Runtime | B/Fix B | 2 | Да | stock release | FSM closed+closure_result |
| backend/apps/orders/services/__init__.py | M | Runtime | Fix B | 2 | Да | transitions | exports |
| backend/apps/admin_api/views/orders.py | M | Runtime | Fix B | 2 | Да | transitions | admin status aliases |
| backend/tests/order_fsm_assertions.py | ?? | Test | Fix B/G | 2 | Да | transitions | shared asserts |
| backend/tests/test_fix_pack_b_order_cancellation.py | ?? | Test | Fix B | 2 | Да | transitions | |
| backend/tests/test_sec003_cancel_releases_stock.py | M | Test | Fix B/G | 2 | Да | transitions+stock | |
| backend/tests/test_func002_func009_cancel_policy.py | M | Test | Fix B/G | 2 | Да | transitions | |
| backend/tests/test_int001_int002_order_fsm.py | M | Test | Fix B/G | 2 | Да | transitions | |
| backend/tests/test_block8_refund_settlement.py | M | Test | Fix B/G | 2 | Да | FSM refund | |
| backend/tests/test_func001_expire_yookassa_sync.py | M | Test | Fix B/G | 2 | Да | expire→closed | |
| backend/tests/test_int004_int005_yookassa_refund_metadata.py | M | Test | Fix B | 2 | Да | refund FSM | |
| backend/tests/test_sber_payments.py | M | Test | Fix B | 2 | Да | payment cancel paths | |

**Count:** 12

### Commit 3 — Checkout / guest / idempotency (19)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| backend/apps/orders/views.py | M | Runtime | Fix D | 3 | Да | cache idempotency | pending claim 409 |
| backend/tests/test_sec005_order_idempotency.py | M | Test | Fix D | 3 | Да | orders.views | |
| backend/tests/test_sec006_guest_access_token.py | M | Test | Fix A | 3 | Да | guest token | |
| backend/tests/test_fix_pack_a_guest_success.py | ?? | Test | Fix A | 3 | Да | guest success | |
| backend/tests/test_order_repay.py | M | Test | Fix D | 3 | Да | payments | |
| backend/tests/test_payment_security.py | M | Test | Fix D | 3 | Да | payments | |
| frontend/src/app/checkout/page.tsx | M | Runtime | Fix D/L | 3 | Да | idempotency helpers | checkout+sticky CTA |
| frontend/src/lib/orders/checkout-idempotency.ts | ?? | Runtime | Fix D | 3 | Да | — | |
| frontend/src/lib/orders/checkout-idempotency.test.ts | ?? | Test | Fix D | 3 | Да | | |
| frontend/src/lib/orders/checkout-success-path.ts | ?? | Runtime | Fix A/D | 3 | Да | | |
| frontend/src/lib/orders/checkout-success-path.test.ts | ?? | Test | Fix A/D | 3 | Да | | |
| frontend/src/lib/api/services/payments.service.ts | M | Runtime | Fix D | 3 | Да | stash | |
| frontend/src/lib/api/services/payments.stash.test.ts | ?? | Test | Fix D | 3 | Да | | |
| frontend/src/app/orders/[id]/success/page.tsx | M | Runtime | Fix A | 3 | Да | guest token | |
| frontend/src/app/orders/[id]/success/page.test.tsx | M | Test | Fix A | 3 | Да | | |
| frontend/src/app/orders/success/page.test.tsx | ?? | Test | Fix A | 3 | Да | | |
| frontend/src/app/orders/[id]/payment/return/page.tsx | M | Runtime | Fix D | 3 | Да | stash | |
| frontend/src/app/orders/[id]/payment/return/page.test.tsx | M | Test | Fix D | 3 | Да | | |
| frontend/src/app/orders/[id]/payment/fail/page.tsx | M | Runtime | Fix D | 3 | Да | stash | |

**Count:** 19

### Commit 4 — Auth refresh / logout (9)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| frontend/src/lib/api/client.ts | M | Runtime | Fix C | 4 | Да | auth-refresh | 401 refresh |
| frontend/src/lib/api/auth-refresh.ts | ?? | Runtime | Fix C | 4 | Да | client | |
| frontend/src/lib/api/auth-refresh.test.ts | ?? | Test | Fix C | 4 | Да | | |
| frontend/src/lib/api/services/auth.service.ts | M | Runtime | Fix C/F | 4 | Да | cookies/staff | cannot split |
| frontend/src/lib/api/services/auth.login-mfa.test.ts | ?? | Test | Fix C/F | 4 | Да | auth.service | |
| frontend/src/lib/auth-mode.ts | M | Runtime | Fix C | 4 | Да | | |
| frontend/src/lib/hooks/useAuth.ts | M | Runtime | Fix C/E | 4 | Да | cart invalidate | |
| frontend/src/lib/hooks/useAuth.logout-cart.test.ts | ?? | Test | Fix E | 4 | Да | useAuth | |
| backend/apps/users/tests.py | M | Test | Fix G | 4 | Да | Stock fixture JWT merge | |

### Commit 5 — AdminGuard / admin UX (11)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| frontend/src/components/admin/AdminGuard.tsx | M | Runtime | Fix F | 5 | Да | staff-access | |
| frontend/src/components/admin/AdminGuard.test.tsx | ?? | Test | Fix F | 5 | Да | | |
| frontend/src/components/admin/AdminQueryError.tsx | ?? | Runtime | Fix E | 5 | Да | errors.ts | |
| frontend/src/components/admin/AdminQueryError.test.tsx | ?? | Test | Fix E | 5 | Да | | |
| frontend/src/lib/errors.ts | M | Runtime | Fix E/F | 5 | Да | | getApiErrorStatus |
| frontend/src/lib/errors.api-status.test.ts | ?? | Test | Fix E | 5 | Да | | |
| frontend/src/lib/api/services/auth.staff-access.test.ts | ?? | Test | Fix F | 5 | Да | auth.service | |
| frontend/src/app/admin/login/page.tsx | M | Runtime | Fix F | 5 | Да | staff access | |
| frontend/src/app/admin/products/[id]/page.tsx | M | Runtime | Fix E | 5 | Да | AdminQueryError | |
| frontend/src/app/admin/users/[id]/page.tsx | M | Runtime | Fix E | 5 | Да | AdminQueryError | |
| frontend/src/app/admin/returns/[id]/page.tsx | M | Runtime | Fix E | 5 | Да | AdminQueryError | |

**Count:** 11

### Commit 6 — Storefront UI + responsive (15)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| frontend/src/app/cart/page.tsx | M | Runtime | Fix E | 6 | Да | | promo removed / states |
| frontend/src/app/cart/page.promo.test.tsx | ?? | Test | Fix E | 6 | Да | | |
| frontend/src/components/features/cart/CartItem.tsx | M | Runtime | Fix L | 6 | Да | | long title wrap |
| frontend/src/app/checkout/checkout-cart-states.test.tsx | ?? | Test | Fix E | 6 | Да | | empty vs error |
| frontend/src/app/orders/[id]/page.tsx | M | Runtime | Fix E | 6 | Да | errors.ts | not-found / mailto |
| frontend/src/app/orders/[id]/order-detail-states.test.tsx | ?? | Test | Fix E | 6 | Да | | |
| frontend/src/app/products/[slug]/ProductPageClient.tsx | M | Runtime | Fix E | 6 | Да | | 1-click removed |
| frontend/src/app/products/[slug]/one-click-removed.test.tsx | ?? | Test | Fix E | 6 | Да | | |
| frontend/src/components/features/products/ProductCard.tsx | M | Runtime | Fix E | 6 | Да | | |
| frontend/src/components/features/stores/StoreSelector.tsx | M | Runtime | Fix E/B2 | 6 | Да | is_warehouse | |
| frontend/src/app/stores/StoresContent.tsx | M | Runtime | Fix E/B2 | 6 | Да | | |
| frontend/src/types/api.ts | M | Runtime | B2/Fix E | 6 | Да | StoreSelector | is_warehouse |
| frontend/src/components/layout/Footer.tsx | M | Runtime | Fix L | 6 | Да | | break-words |
| frontend/src/lib/theme/spacing.ts | M | Runtime | Fix L | 6 | Да | Header | 360 overflow |
| frontend/src/lib/theme/responsive-contracts.test.ts | ?? | Test | Fix L | 6 | Да | spacing | |

**Count:** 15

### Commit 7 — SEO (5)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| frontend/src/lib/seo/public-site-routes.ts | ?? | Runtime | Fix I | 7 | Да | | shared routes |
| frontend/src/lib/seo/public-site-routes.test.ts | ?? | Test | Fix I | 7 | Да | | |
| frontend/src/app/sitemap.ts | M | Runtime | Fix I | 7 | Да | public-site-routes | |
| frontend/src/app/robots.ts | M | Runtime | Fix I | 7 | Да | | |
| frontend/src/app/site-map/page.tsx | M | Runtime | Fix I | 7 | Да | public-site-routes | |

**Count:** 5

### Commit 8 — Documentation (23)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| docs/API.md | M | Documentation | Fix H | 8 | Да | trailing ws note | API sync |
| docs/audit/BLOCK2_STOCK_RECONCILIATION_REPORT.md | ?? | Documentation | B2 | 8 | Да | | |
| docs/audit/BLOCK3_SERIES_CART_REPORT.md | ?? | Documentation | B3 | 8 | Да | | |
| docs/audit/BLOCK4_ORDERS_LOCKS_TRANSACTIONS_REPORT.md | ?? | Documentation | B4 | 8 | Да | | |
| docs/audit/BLOCK5_SECURITY_DATA_INTEGRITY_REPORT.md | ?? | Documentation | B5 | 8 | Да | | |
| docs/audit/BLOCK6_PERFORMANCE_REPORT.md | ?? | Documentation | B6 | 8 | Да | | |
| docs/audit/BLOCK7_REPORTING_GUARDS_REPORT.md | ?? | Documentation | B7 | 8 | Да | | |
| docs/audit/BLOCK8_FULL_SYSTEM_AUDIT_REPORT.md | ?? | Documentation | B8 | 8 | Да | | |
| docs/audit/FIX_PACK_A_GUEST_SUCCESS_REPORT.md | ?? | Documentation | A | 8 | Да | | |
| docs/audit/FIX_PACK_B_ORDER_CANCELLATION_REPORT.md | ?? | Documentation | B | 8 | Да | | |
| docs/audit/FIX_PACK_C_AUTH_REFRESH_REPORT.md | ?? | Documentation | C | 8 | Да | | |
| docs/audit/FIX_PACK_D_CHECKOUT_PAYMENT_REPORT.md | ?? | Documentation | D | 8 | Да | | |
| docs/audit/FIX_PACK_E_UI_INTEGRITY_REPORT.md | ?? | Documentation | E | 8 | Да | | |
| docs/audit/FIX_PACK_F_ADMIN_GUARD_REPORT.md | ?? | Documentation | F | 8 | Да | | |
| docs/audit/FIX_PACK_G_FSM_V2_TESTS_REPORT.md | ?? | Documentation | G | 8 | Да | | |
| docs/audit/FIX_PACK_H_API_DOCS_REPORT.md | ?? | Documentation | H | 8 | Да | | |
| docs/audit/FIX_PACK_I_SITEMAP_REPORT.md | ?? | Documentation | I | 8 | Да | | |
| docs/audit/FIX_PACK_J_RELEASE_HYGIENE_REPORT.md | ?? | Documentation | J | 8 | Да | | |
| docs/audit/FIX_PACK_K_LOAD_TEST_REPORT.md | ?? | Documentation | K | 8 | Да | | |
| docs/audit/FIX_PACK_L_RESPONSIVE_QA_REPORT.md | ?? | Documentation | L | 8 | Да | | |
| docs/audit/RELEASE_1_FINAL_INVENTORY.md | ?? | Documentation | Rel1 | 8 | Да | | |
| docs/audit/RELEASE_2_COMMIT_MANIFEST.md | ?? | Documentation | Rel2 | 8 | Да | | this file |
| docs/audit/RINGOO_ONEC_FULL_TECHNICAL_AUDIT.md | ?? | Documentation | OneC | 8 | Да | | |

**Count:** 23

### Commit 9 — Tooling (3)

| Path | Git | Category | Block/Pack | Commit | Required | Dependency | Reason |
|---|---|---|---|---|---|---|---|
| backend/scripts/b8_018_load_benchmark.py | ?? | Tooling | K | 9 | Нет* | Commit 1 code | полезен для повтора B8-018 |
| backend/scripts/b8_018_rerun_dryrun.py | ?? | Tooling | K | 9 | Нет* | load_benchmark | helper |
| backend/scripts/b8_018_zero_smoke.py | ?? | Tooling | K | 9 | Нет* | stock apply | smoke |

\*Required для **runtime** = Нет; Recommended для **поддержки** = Да (оставить в манифесте как optional commit).

---

## 8. Сводка количества и покрытие status

| Bucket | Files |
|---:|
| Commit 1 | 42 |
| Commit 2 | 12 |
| Commit 3 | 19 |
| Commit 4 | 9 |
| Commit 5 | 11 |
| Commit 6 | 15 |
| Commit 7 | 5 |
| Commit 8 | 23 |
| Commit 9 | 3 |
| Exclude (in status) | 7 |
| **Sum** | **146** |

До записи манифеста: 145 строк status.  
После появления `RELEASE_2_COMMIT_MANIFEST.md` (уже в Commit 8): **146** = 139 включаемых + 7 exclude.

---

## 9. Зависимости между коммитами

```
1 (OneC/stock/migrations)
 └── 2 (FSM) —— рекомендуется после 1 (cancel→release stock)
      └── 3 (checkout/guest) —— рекомендуется после 2
4 (auth) —— независимо от 1; желателен до 5
 └── 5 (admin guard)
3 + 6 —— 6 может идти после 3 (checkout page уже в 3)
7 (SEO) —— независимо
8 (docs) —— после кода 1–7
9 (scripts) —— после 1
```

---

## 10. Блокеры и риски

| Item | Level | Notes |
|---|---|---|
| Подтверждение манифеста вами | Blocker to `git add` | |
| stores.0008 data migration | High at deploy | slug mapping / tech-sklad create |
| stores.0009 PROTECT | Medium | hard-delete products blocked |
| Commit 3 commerce | High | must ship with matching BE/FE |
| docs/API.md trailing whitespace | Low | fix before/during Commit 8 |
| Full test suite not re-run after Fix L | Medium | spot-check before push |
| Commit 9 optional | — | можно пропустить |

**Блокеров к подготовке коммитов (кроме вашего ACK): нет.**

---

## 11. Итоговый порядок (коротко)

1. OneC + stock + migrations 0008/0009 + mapping  
2. FSM v2 + cancel tests + admin order status  
3. Checkout idempotency + guest success + payments stash (+ checkout page)  
4. Auth refresh / cookies / logout cart  
5. AdminGuard + AdminQueryError + admin detail/login  
6. Storefront UI + responsive contracts  
7. SEO public routes  
8. Documentation (+ trim API.md whitespace отдельным микро-fix по ACK)  
9. (Optional) B8-018 scripts  

Exclude: `промпт.txt`, `Описание работ.txt`, 4×`.docx`, `frontend/AGENTS.md`; `backend/var/` ignored.

---

## Остановка

Манифест готов. **`git add` / `commit` / `push` не выполнялись.**  
Следующий шаг — только после вашего подтверждения этого файла.
