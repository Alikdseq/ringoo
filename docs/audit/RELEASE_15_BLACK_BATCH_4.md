# RELEASE 15 — BLACK BATCH 4/6

**Дата/время:** 2026-11-16 13:54:36 +03:00  
**Основание:** RELEASE 14 = PASS WITH WARNINGS  
**Вердикт:** **PASS**

---

## 1. HEAD / Black

| | До | После |
|---|---|---|
| Branch | `main` | `main` |
| HEAD | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` | `fcc23d001ddea397e152adde4ea4c86f25ff74e3` |
| Black | 26.1.0 | 26.1.0 |

Remaining до: **80** (`black_remaining_after_batch3.txt`).  
Исключены: R9 (21), R12–R14 (90), HOLD `scripts/b8_018_zero_smoke.py`, untracked, tmp/var.  
Пересечений с предыдущими партиями: **0**.

---

## 2. Файлы партии (30)

Список: `backend/var/r11/black_batch4_files.txt`

### apps/ (9)
1. `apps/users/apps.py`
2. `apps/users/jwt_cookies.py`
3. `apps/users/management/commands/cleanup_deactivated_users.py`
4. `apps/users/password_reset.py`
5. `apps/users/tests.py`
6. `apps/users/tests_legal.py`
7. `apps/users/tests_security_data.py`
8. `apps/users/views.py`
9. `apps/wishlist/tests.py`

### integrations/ (12)
10. `integrations/email_service.py`
11. `integrations/maps_service.py`
12. `integrations/onec/catalog_sync.py`
13. `integrations/onec/client.py`
14. `integrations/onec/importer.py`
15. `integrations/onec/inbound.py`
16. `integrations/onec/orders.py`
17. `integrations/onec/parser.py`
18. `integrations/onec/registration.py`
19. `integrations/onec/url_utils.py`
20. `integrations/sber/client.py`
21. `integrations/yookassa/client.py`

### tests/ (9)
22. `tests/test_admin_integrity.py`
23. `tests/test_admin_mfa.py`
24. `tests/test_block8_catalog_guards.py`
25. `tests/test_block8_refund_settlement.py`
26. `tests/test_color_onec_mapping.py`
27. `tests/test_concurrency_postgres.py`
28. `tests/test_func003_price_consistency.py`
29. `tests/test_func007_bonus_flag.py`
30. `tests/test_func011_func004_color_and_cart.py`

`scripts/` / `config/` не брались — приоритетные категории заполнили партию.

---

## 3. До / после

| | |
|---|---|
| До (партия) | 30 would reformat |
| Black write | **30 reformatted** |
| `black --check` (партия) | **30 unchanged** (PASS) |
| Полный `black --check .` | **50** would reformat (было 80; −30) |

Остаток: `backend/var/r11/black_remaining_after_batch4.txt` (**50**).

`git diff --stat`: `30 files changed, 259 insertions(+), 632 deletions(-)`.

---

## 4. Проверки

| Проверка | Результат |
|---|---|
| `black --check` (партия) | **PASS** |
| `git diff --check` | **PASS** (LF→CRLF warning на `jwt_cookies.py` — line endings, не логика) |
| Django check (test) | **PASS** |
| makemigrations --check --dry-run | **PASS** |
| pytest users/legal + wishlist + selected tests | **46 passed** |
| pytest color mapping + block8 refund | **9 passed** |
| **Итого точечные** | **55 passed** |

Promotions 403 из R14 в эту партию не входили и не «чились».  
`cryptography` / другие deps не устанавливались.

---

## 5. Diff = только форматирование

Samples (`users/views.py`, `integrations/onec/importer.py`):

- снятие лишних скобок вокруг `or`-цепочки;
- сжатие многострочных ORM/`dict`/`list` конструкторов;
- без смены импортов, условий, аргументов, типов, бизнес-логики.

---

## 6. Ограничения

- Полный Black CI ещё красный: **50** файлов.
- Не диагностировался и не чинился promotions 403 (вне scope).
- Не ставились зависимости.

---

## 7. Git

HEAD без коммита. Новые M: 30 файлов §2.  
Прежние dirty R8–R14 + untracked audit/HOLD сохранены.

---

## Вердикт

**PASS** — batch 4/6 отформатирован, проверки и точечные тесты зелёные, остаток Black **50**.

**Остановка.** Batch 5 — только после согласования.  
**Никаких коммитов и push.**
