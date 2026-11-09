# BLOCK 10 — Django Migration Finalization (RenameIndex Drift)

Дата: 2026-11-09
Вердикт: **READY FOR VPS MIGRATIONS** (после backup целевой БД; не означает готовность live pay / 1С / коммерческого запуска).

Исходный Git на старте блока: `main` @ `f334c9f` (= `origin/main`).

## 1. Причина проблемы

`python manage.py makemigrations --check --dry-run` предлагал серии `RenameIndex` по приложениям `bonus`, `content`, `orders`, `payments`, `stores`, `wishlist`, `users`.

**Корневая причина (Scenario A):** в моделях `Meta.indexes` индексы были объявлены **без явного `name=`**. Django при автодетекте вычисляет имя хешем. Имена, уже зафиксированные в migration state (часто заданы вручную в CreateModel/AddIndex), **не совпадали** с именами, которые текущий Django 5.1.15 генерирует для тех же полей. Структура индексов (поля) совпадала; отличались только имена.

Это не расхождение схемы PostgreSQL «поля vs поля», а рассинхрон **model state ↔ migration state** по именам.

Прецедент уже был в проекте: `ProductColor` закреплён комментарием «Имя из 0003 — иначе makemigrations предлагает RenameIndex».

Отдельно (не RenameIndex) оставался **state-only** drift полей:

| Поле | Суть |
|---|---|
| `Order.confirmation_email_sent_at` | изменён `help_text` |
| `Payment.merchant_order_number` | изменён `verbose_name` |
| `ProductImage.image` | `upload_to` со строки `products/%Y/%m/` на callable `product_image_upload_to` |
| `ConsentRecord.consent_type` | расширены `choices` |
| `CustomUser` | `AlterModelManagers` + синхронизация inherited AbstractUser meta (`date_joined` без `blank=True`, help_text) |

Эти изменения **не требуют RenameIndex** и на PostgreSQL не переименовывают индексы; они синхронизируют Django state.

## 2. Затронутые модели (индексы)

| Приложение | Модель | Имя в migration state (канон) | Было у модели (auto) | Миграция создания | Состояние после фикса |
|---|---|---|---|---|---|
| bonus | BonusAccount | `bonus_bonus_user_id_8a1f0d_idx` | `…84d633…` | 0001 | pinned in model |
| bonus | BonusAccount | `bonus_bonus_updated_2c2b2a_idx` | `…3fd0d4…` | 0001 | pinned |
| bonus | BonusTransaction | `bonus_bonus_account_7e8f3c_idx` | `…e4ccbb…` | 0001 | pinned |
| bonus | BonusTransaction | `bonus_bonus_created_1d4e5b_idx` | `…f454be…` | 0001 | pinned |
| bonus | BonusTransaction | `bonus_bonus_reason_9a2b3c_idx` | `…28ee14…` | 0001 | pinned |
| bonus | BonusTransaction | `bonus_bonus_related_4e5f6a_idx` | `…3cc73b…` | 0001 | pinned |
| content | PageGalleryImage | `content_pag_placeme_idx` | `…83abfe…` | 0002 | pinned |
| orders | Order | `orders_orde_onec_sy_7a1c2d_idx` | `…374a6f…` | 0007 | pinned (+ остальные Order indexes для профилактики) |
| payments | Payment | `payments_pa_order_i_7e0e0e_idx` | `…a76289…` | 0001 | pinned |
| payments | Payment | `payments_pa_created_e4e6f7_idx` | `…b8a300…` | 0001 | pinned |
| stores | Stock | `stores_stoc_onec_se_4b8e1a_idx` | `…25ca7d…` | 0006 | pinned |
| wishlist | WishlistItem | `wishlist_wi_user_id_7a8c2a_idx` | `…1fe9fd…` | 0001 | pinned |
| wishlist | WishlistItem | `wishlist_wi_product_2b9f3c_idx` | `…2322a5…` | 0001 | pinned |
| users | DeliveryAddress | `users_deladdr_user_idx` / `users_deladdr_user_default_idx` | auto `users_deliv_*` | 0001 | pinned |
| users | ConsentRecord | `users_conse_user_id_6e0f0a_idx` / `users_conse_order_i_8c8f8b_idx` | auto hash | 0004 | pinned |

**Не создавались** миграции `RenameIndex` — они были бы опасны/шумны для уже существующих БД с именами из state.

## 3. Выполненные изменения

### Модели (pin `name=`)

- `backend/apps/bonus/models.py`
- `backend/apps/content/models.py`
- `backend/apps/orders/models.py`
- `backend/apps/payments/models.py`
- `backend/apps/stores/models.py`
- `backend/apps/wishlist/models.py`
- `backend/apps/users/models.py`

### Новые миграции (state sync, без RenameIndex)

- `orders/migrations/0011_block10_state_sync.py`
- `payments/migrations/0005_block10_state_sync.py`
- `products/migrations/0009_block10_state_sync.py`
- `users/migrations/0006_block10_state_sync.py`

## 4. Проверки PostgreSQL

| Параметр | Значение |
|---|---|
| Версия | PostgreSQL **15.15** (`postgres:15-alpine`, контейнер `ringoo_db`) |
| База | изолированная `ringoo_mig_block10` (создана/удалена; **не** рабочая `ringoo`) |
| `migrate --noinput` с нуля | **OK** (включая `*.0011/0005/0009/0006_block10_state_sync`) |
| Индексы в `pg_indexes` | все 14 канонических имён из таблицы §2 присутствуют |
| `makemigrations --check --dry-run` после migrate | **No changes detected** |
| `migrate --plan` на той же БД | **No planned migration operations** |

Рабочая БД приложения **не** изменялась.

## 5. Регрессионные тесты

| Набор | Результат |
|---|---|
| Targeted Block 8/9 suite (98): INV-001/002, PAY-001/sec007, onec, sec001–003, payment_security, bank_transfer | **OK** |
| `apps.stores` / `products` / `orders` / `cart` tests | **88 OK** |
| `check --deploy` (container, production settings, dummy secrets) | exit 0 (известные W002/spectacular + security warnings на dummy SSL) |

## 6. Git

| Поле | Значение |
|---|---|
| Ветка | `main` |
| Коммит | `fix: resolve Django migration index drift` *(SHA после push)* |
| Push | ordinary `git push origin main` (no force) |

Исключено из коммита: локальные `.env*`, `*.docx`, `промпт.txt`, `copy-site/`.

## 7. Остаточные риски

- На уже развёрнутых БД индексы уже носят **старые (канонические)** имена — pin в моделях и state-sync миграции это подтверждают; `RenameIndex` **не** нужен.
- State-sync AlterField не меняют физические колонки (help_text/verbose_name/choices/upload_to/managers) — риск потери данных: **нет**.
- Live VPS / restore drill / ЮKassa / 1С: **не** проверялись в этом блоке.
- Третьи приложения (axes/auth verbose_name при `LANGUAGE_CODE=ru`) могут шуметь при полном ProjectState-diff, но `makemigrations` по project apps даёт **No changes detected**.

## 8. Рекомендации для VPS

1. Backup PostgreSQL.
2. `git pull --ff-only origin main`.
3. Только overlay:
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production …`
4. `python manage.py showmigrations`
5. `python manage.py migrate --plan` — ожидаются только неприменённые, включая `*_block10_state_sync` и ранее не применённые `0004`/`0008` при первом деплое.
6. `python manage.py migrate --noinput`
7. `python manage.py makemigrations --check --dry-run` → **No changes detected**
8. **Не** запускать `makemigrations` на VPS для «починки» имён.
9. **Не** использовать `--fake` / `--fake-initial` без отдельного инцидента.

---

**Итог:** RenameIndex drift закрыт закреплением канонических имён в моделях + state-sync миграциями. Миграции готовы к применению на VPS после резервного копирования.
