# Comprehensive Security Audit — Ringo

| Поле | Значение |
|------|----------|
| Дата | 2026-11-02 |
| HEAD | `8a0bd5f` (`main` = `origin/main`) |
| Режим | **Только аудит.** Без исправлений, commit, push, deploy, миграций, реальных платежей и POST в 1С. |
| Секреты | Значения паролей/токенов/`SECRET_KEY` **не** выводятся. |
| Предыдущие отчёты | Перечитаны; статусы **перепроверены по коду/тестам**, не приняты на слово. |
| Доступ к VPS | **Не предоставлен** — OS/SSH/firewall/live ports = «Не проверено». |
| Docker runtime | На момент аудита compose **не** использовался для live-эксплойта; выводы по портам — **анализ конфигурации**. |

**Общий вердикт:** **SECURITY CONDITIONAL**

Публикация на отдельном VPS допустима **только после** обязательных инфраструктурных и конфигурационных мер (разд. 22). Критический риск сейчас — **неверно развёрнутый** compose/env (открытые БД/Redis, dev-секреты), а не подтверждённый «открытый admin без пароля» в коде приложения.

---

## 1. Executive Summary

| Область | Краткий итог |
|---------|--------------|
| App auth / RBAC | Staff API за `IsStaff` + группы; назначение `is_staff`/`groups` — только superuser (**код + прошлые тесты**). |
| Django Admin | Путь настраиваем (`DJANGO_ADMIN_URL`), **MFA/OTP по умолчанию выкл.** Axes есть. |
| Платежи | Клиент **не** может выставить paid; callback token fail-closed в prod; **57** security-релевантных тестов **passed** в этой сессии. |
| Пароли | **Argon2** primary hasher. |
| PII | В БД в открытом виде (типично для e-commerce); шифрование полей **не** внедрено. |
| Docker Compose | **Публикует** Postgres/Redis на хост; пароль БД default `postgres`; Redis без пароля, если env пуст. Prod overlay **не** закрывает порты и **наследует** `env_file` development. |
| Секреты в Git (имена файлов) | В индексе только `.env.example` / docs; реальные `.env*` в `.gitignore`/`.dockerignore`. Полный gitleaks history — **не установлен**. |
| Supply chain | `pip-audit`: известных vulns не найдено. `npm audit --omit=dev`: метаданные без critical в JSON-снимке сессии (ранее moderate Sentry/glob — контролировать отдельно). |
| Server hardening | **Не проверено** (нет согласованного доступа). |
| Backup/RPO | **Не проверено** в коде/ops — план не найден как исполняемый артефакт. |

**Подтверждено тестированием (эта сессия):**  
`tests/test_payment_security.py` + `test_admin_integrity.py` + `apps/users/tests.py` → **57 passed**.

**Подтверждено анализом кода:** конфигурация compose/settings/permissions/payments/orders/frontend storage/CSP.

**Не проверено:** live firewall VPS, pg_hba на сервере, TLS cipher suites домена, восстановление backup, полный git-history secret scan tooling, агрессивный pentest, DDoS.

---

## 2. Архитектура и модель угроз

### 2.1 Границы доверия

```
[Internet]
   │ HTTPS (ожидается reverse proxy — не в полном prod compose)
   ▼
Next.js (frontend :3000) ──API──► Django/DRF (web :8000)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              PostgreSQL         Redis              Celery
              (данные)        (cache/broker)      (tasks)
                    │
         [внешние: 1С / Sber / касса — должны быть OFF]
```

| Зона | Должна быть | Фактически в default compose |
|------|-------------|------------------------------|
| Frontend/Backend HTTP | Публично через 443 | Порты 3000/8000 на хост |
| PostgreSQL | Только Docker network | **Публикуется** `${DB_PORT:-5436}:5432` |
| Redis | Только Docker network | **Публикуется** `${REDIS_PORT:-6380}:6379` |
| Django Admin /admin API | Auth + MFA + желательно VPN/IP allowlist | Auth; MFA optional |

### 2.2 Данные и доступ

См. разд. 3. Роли: аноним → аутентифицированный → staff+group → superuser.

### 2.3 STRIDE (сжато)

| Угроза | Сценарий | Вероятность* | Последствия | Защита сейчас | Остаточный риск |
|--------|----------|--------------|-------------|----------------|-----------------|
| **S** Spoofing | Brute-force admin/JWT | Средняя без MFA/strong passwords | Admin / PII | Axes + throttle login | MFA off by default |
| **S** | Подделка Sber callback | Средняя если токен слабый/отсутствует | Ложный paid | Token + bank status sync | Нужен prod token |
| **T** Tampering | Подмена цены/delivery_cost | Низкая (сервер пересчитывает) | Финансовые потери | Server-side totals | Тесты cover |
| **T** | Подмена paid через API | Низкая | Ложный paid | Fail-closed sync | — |
| **R** Repudiation | Staff меняет заказы без аудита | Средняя | Споры | `log_admin_action` частично | Неполный coverage всех действий |
| **I** Disclosure | Открытый Postgres/Redis | **Высокая при наивном deploy** | Полная БД / сессии | Зависит от firewall | **Блокер** |
| **I** | UUID+phone → pay/cancel | Средняя при утечке UUID | Чужой заказ/оплата | Throttle | Не order_number для pay |
| **I** | `/health/` exception text | Низкая–средняя | Внутренняя инф. | — | Medium |
| **D** DoS | Flood API / order create | Средняя | Деградация | DRF throttles | Нет WAF/CDN proof |
| **E** EoP | Staff → is_staff | Закрыто для non-superuser | — | validate_is_staff | Bonus API только IsStaff |

\*При условии публичного VPS без доп. hardening.

### 2.4 Приоритетные сценарии злоумышленника

1. Найти открытый `:5436`/`:6379` → дамп БД / flush Redis.  
2. Подобрать пароль Django Admin без OTP.  
3. Утечка JWT из XSS при режиме localStorage.  
4. Злоупотребление guest order endpoints (UUID/phone).  
5. Compromised host → чтение `.env` / volume backups.

---

## 3. Инвентаризация защищаемых данных

| Данные | Где | Вид | Кто читает | Сеть | Логи | Backup | Доп. шифрование |
|--------|-----|-----|------------|------|------|--------|-----------------|
| Пароль пользователя | PostgreSQL `users` | Argon2 hash | Auth subsystem | HTTPS login | Не должен | Да, как hash | Не нужно (hash) |
| Телефон, email, ФИО | User/Profile/Order | Plaintext | User, staff groups | API HTTPS | Риск в логах ошибок | Да | Опционально at-rest disk |
| Адрес доставки | DeliveryAddress / Order | Plaintext | Owner, staff | API | Риск | Да | Disk/backup |
| История заказов | Order/OrderItem | Plaintext | Owner/staff; track+phone | API | — | Да | — |
| JWT access/refresh | Cookie HttpOnly (preferred) или localStorage | Bearer | Browser | HTTPS | Не полные токены | N/A | Secure/HttpOnly |
| Sber mdOrder / payment ids | Payment | Plaintext IDs | Staff, sync | Callback | Partial | Да | Не PAN (нет карточных данных) |
| ONE_C / Sber credentials | Env | Secrets | App process | Internal | Запрещено | Env backups | Vault/secret manager |
| Session / Axes | DB/cache | — | App | Internal | Failures | — | — |

**Карточные данные PAN/CVV в системе не хранятся** (редирект на банк) — подтверждено архитектурой payments; live Sber **не** вызывался.

---

## 4. Криптография и хеширование

| Проверка | Результат | Доказательство |
|----------|-----------|----------------|
| PasswordHasher | **Argon2** → PBKDF2 fallback | `base.py` PASSWORD_HASHERS ~178–182 |
| Самописный hash | Не найден | Анализ кода |
| Пароли plaintext | Не найдены в моделях | Анализ |
| Field-level PII encryption | **Нет** | Анализ моделей |
| Disk/backup encryption | **Не проверено** | Нет доступа к серверу |
| TLS публичный | Ожидается proxy; `SECURE_SSL_REDIRECT` True (non-Vercel) | `production.py` |
| `SECURE_PROXY_SSL_HEADER` | Только `ON_VERCEL` | **High** для nginx VPS |
| JWT signing | `SECRET_KEY` / SIMPLE_JWT | Код |
| Vercel SECRET_KEY derive | Детерминированный hash от project id если слабый ключ | `production.py` 40–50 — **не использовать как постоянную схему** |

**Рекомендация:** at-rest encryption диска БД + шифрованные offsite backups; field encryption — только после отдельного key-management design (ключ **не** рядом с БД).

---

## 5. Аутентификация и авторизация

| Контроль | Статус | Evidence |
|----------|--------|----------|
| JWT + optional HttpOnly cookies | Есть | settings + frontend auth-mode |
| Login throttle | 5/minute anon | DEFAULT_THROTTLE_RATES |
| django-axes | failure limit 8, cooloff | base.py |
| Registration throttle | Есть | auth_register scope |
| Staff API | IsAuthenticated + IsStaff + group | permissions.py |
| Public user list | Нет (admin only) | UserAdminListView |
| Order detail auth | IsAuthenticated + queryset owner | orders/views |
| Guest track | order_number **и** phone | OrderTrackView |
| Guest pay | UUID + phone (без order_number) | payments `_can_access_order` |
| Privilege: is_staff/groups | Superuser only | UserAdminUpdateSerializer |

**Cookie-mode:** рекомендуется для prod (`NEXT_PUBLIC_USE_AUTH_COOKIES=1`). localStorage JWT — **Medium** XSS impact.

---

## 6. Django Admin Security

| Вопрос | Ответ | Evidence type |
|--------|-------|---------------|
| Доступ без auth? | **Не подтверждено** открытие без credentials в коде; стандартный login Django | Code analysis |
| RBAC Admin API | Группы `ringoo_*` | Code |
| FE AdminGuard | UI only; сервер enforce | Code |
| MFA/OTP | `ADMIN_OTP_ENABLED` default **false** | Code — **High** |
| Смена URL | `DJANGO_ADMIN_URL` (default `admin`) | Code — obscurity only |
| Brute-force | Axes + throttle | Code |
| VPN/IP allowlist | **Не в приложении** | Unverified / missing |
| Audit log | `log_admin_action` на user update | Code partial |

**Не подтверждена** возможность неавторизованного доступа к admin panel через известный bypass в текущем коде.

---

## 7. API Security (ключевые классы)

| Класс endpoints | Auth | Риск |
|-----------------|------|------|
| Catalog/products/stores public | AllowAny | OK (публичные данные) |
| Cart | Session/user + throttle | OK |
| Orders create | Auth/anon + throttle; server prices | OK |
| Orders detail | Authenticated owner | OK |
| Orders track/status | AllowAny + number+phone | Acceptable shared-secret |
| Orders cancel | AllowAny + owner/phone | Abuse if UUID leaked |
| Payments pay/status | AllowAny + access check + throttle | Phone+UUID |
| Payments callback | AllowAny + shared token + bank sync | OK when configured |
| `/api/v1/admin/*` | Staff+group (bonus: IsStaff only) | Bonus = Medium |
| `/health/` | Public, may leak exception | Medium |
| API docs | `API_DOCS_PUBLIC` default False in prod | OK |

Mass assignment paid/status — закрыто ранее; **перепроверено** тестами payment_security.

---

## 8. PostgreSQL Security

| Проверка | Статус |
|----------|--------|
| Не слушать интернет | **Конфиг compose публикует порт** — на VPS без firewall = Critical |
| App не superuser | Default `postgres` user в compose — **High** |
| Отдельные роли migrate/app | **Не реализовано** в compose |
| Сильный пароль | Default `postgres` — Critical если не переопределён |
| pg_hba / SSL | **Не проверено** на сервере |
| SQL injection | ORM/DRF; raw SQL не аудировался построчно полностью — residual Low |
| Encryption at rest / dumps | **Не проверено** |

---

## 9. Redis / Celery Security

| Проверка | Статус |
|----------|--------|
| Порт наружу | **Да в compose** (`6380:6379`) |
| Пароль | Опционален; пустой → `redis-server` без requirepass |
| CELERY broker | `REDIS_URL` без пароля по умолчанию |
| Публичный запуск задач | Не найден произвольный task trigger endpoint |
| Секреты в task args | Риск логирования — code review residual |
| Dangerous deserialize | Celery JSON/default — стандартный риск при доступе к broker |

---

## 10. Docker Security

| Проверка | Prod Dockerfile | Dev / default compose |
|----------|-----------------|------------------------|
| Non-root | `USER django` / `USER nextjs` | Dev image — root typical |
| Privileged / docker.sock | Не найдено в compose | — |
| Publish DB/Redis | — | **Да** |
| Bind-mount code | Prod overlay frontend volumes cleared; **web всё ещё наследует** `./backend:/app` из base | Dev |
| env_file development | Prod **не** сбрасывает | **Critical misconfig path** |
| Resource limits | Не заданы | Medium |
| Healthchecks | Есть | Есть |
| Fixed image tags | `postgres:15-alpine`, `redis:7-alpine` (mutable tags) | Low/Medium supply |

`docker-compose.no-host-db-redis-ports.yml` существует — **обязан** входить в prod-профиль.

---

## 11. Server / OS Security

**Не проверено** — нет согласованного доступа к серверу.

Требуется отдельно: SSH keys only, firewall 80/443, fail2ban, unattended upgrades, Docker API localhost only, no phpMyAdmin, disk encryption.

---

## 12. Network Security

| Тема | Статус |
|------|--------|
| TLS termination | Не в репо как полный nginx/Caddy prod | Unverified |
| HSTS | 1 year в Django production | Aggressive for first cutover |
| Internal TLS DB/Redis | Обычно plaintext в Docker network | Acceptable on single host; not across WAN |
| Host header | ALLOWED_HOSTS enforced if DEBUG False | Code |

---

## 13. Frontend Security

| Тема | Статус |
|------|--------|
| NEXT_PUBLIC_* | Только публичные; org INN etc. — не секреты auth | OK pattern |
| Source maps | Sentry config: sourcemaps disabled (prior audit) | Verify on build |
| dangerouslySetInnerHTML | JSON-LD + uiMode bootstrap (fixed strings) | Low residual |
| Tokens | Cookie preferred; localStorage fallback | Medium if cookies off |
| CSP | Есть; `unsafe-inline`/`unsafe-eval` в script-src | Medium |
| Admin routes | Client guard + server API | OK if API enforced |

---

## 14. OWASP Top 10 / ASVS (сводка)

| Категория | Оценка |
|-----------|--------|
| A01 Broken Access Control | В целом сильно; guest UUID+phone, bonus IsStaff — residual |
| A02 Cryptographic Failures | Argon2 OK; PII plaintext; Vercel key derive concern |
| A03 Injection | ORM; 1С XML via defusedxml; zip path hardened previously |
| A04 Insecure Design | Online pay UX / empty form_url → success (pre-prod report) |
| A05 Misconfiguration | **Compose/env/DEBUG** — главный блокер |
| A06 Vulnerable Components | pip clean; npm monitor |
| A07 Auth Failures | Axes+throttle; MFA optional |
| A08 Integrity Failures | Payment sync fail-closed — tested |
| A09 Logging/Monitoring | Partial; health leaks; no SIEM proof |
| A10 SSRF | ONE_C URL path validated; **no private-IP block** in `url_utils.py` — risk if enabled + malicious URL in env |

---

## 15. DoS / Abuse Protection

Есть: DRF throttles (auth, orders, payments, cart, CRM).  
Нет доказательств: CDN/WAF, nginx connection limits, disk-full alerts, Celery queue caps на сервере.

Нагрузочные тесты **не** выполнялись (запрет).

---

## 16. Logging / Monitoring

- Axes lockouts / admin user changes — частично.  
- Sentry optional (DSN).  
- Запрет логировать пароли — by design; **не** доказано отсутствие утечек во всех except paths.  
- `/health/` может отдать `str(e)` БД/кэша.  
- Централизованный SOC — **не проверено**.

---

## 17. Supply Chain Security

| Инструмент | Результат |
|------------|-----------|
| pip-audit (requirements.txt) | No known vulns in resolved set |
| npm audit --omit=dev | Нет critical в JSON metadata снимка; ранее moderate transitive Sentry |
| Lockfiles | Присутствуют |
| gitleaks/trufflehog/Trivy/Bandit/Semgrep | **Не запускались** (не установлены / не в scope без изменения среды) |
| Git tracked secrets (filenames) | Только examples |

---

## 18. Backup / Recovery

В репозитории **нет** подтверждённого автоматического encrypted offsite backup + tested restore.  
**Статус: Не проверено / отсутствует как код.** Блокер ops для «безопасности данных», не для HTTP-слоя.

---

## 19. Найденные уязвимости / риски

### Critical

| ID | Название | Компонент | Файл | Описание | Атака | Impact | Вероятность | Evidence | Fix | Verify |
|----|----------|-----------|------|----------|-------|--------|-------------|----------|-----|--------|
| CSA-C1 | Published Postgres + weak default | Compose | `docker-compose.yml` 36–41 | Порт БД на хост; default password `postgres` | Скан портов → connect → dump | Полная БД / PII | Высокая на «голом» VPS | Code analysis | Не публиковать порт; сильный пароль; non-superuser role; firewall | `ss`/`nmap` снаружи: closed |
| CSA-C2 | Published Redis optional auth | Compose | `docker-compose.yml` 52–69 | Redis снаружи; без пароля если env пуст | Redis → session/cache/Celery | RCE/queue abuse / data | Высокая | Code analysis | requirepass; no publish; network internal only | External connect fails |
| CSA-C3 | Prod inherits `.env.development` | Compose/settings | `docker-compose.yml` 94–95; `docker-compose.prod.yml`; `base.py` load_dotenv | Prod gunicorn + development env file | DEBUG/dev secrets в «prod» | Traceback, CORS, weak keys | Высокая при слепом `-f prod` | Code analysis | Отдельный prod env_file; не load development | Process env inspection (ops) |
| CSA-C4 | DEBUG bypasses SECRET_KEY/ALLOWED_HOSTS gates | Settings | `production.py` 14–58 | `DEBUG=True` пропускает жёсткие проверки | Misconfig → debug exposure | Info disclosure | Средняя–высокая | Code analysis | Fail closed: запретить DEBUG в production module | `manage.py check --deploy` in image |

### High

| ID | Название | Файл | Суть | Fix |
|----|----------|------|------|-----|
| CSA-H1 | MFA/OTP admin default off | `base.py` ADMIN_OTP | Privileged accounts без TOTP | `ADMIN_OTP_ENABLED=1` + enroll |
| CSA-H2 | App DB role = postgres default | compose | Избыточные права | Least-privilege role |
| CSA-H3 | SECURE_PROXY_SSL_HEADER only Vercel | `production.py` | Broken secure cookies behind nginx | Set header for VPS |
| CSA-H4 | Prod compose incomplete | `docker-compose.prod.yml` | Bind-mount, ports, no migrate story | Hardened compose profile |
| CSA-H5 | Guest pay by UUID+phone | `payments/views.py` `_can_access_order` | Утечка UUID → действия по заказу | Требовать order_number+phone как track |
| CSA-H6 | Checkout online UX / empty form_url | FE checkout (pre-prod) | Ложный success | Hide online; fail closed |
| CSA-H7 | Backup/encryption unproven | Ops | Потеря/кража дампов | Offsite encrypted backups + restore drill |
| CSA-H8 | Vercel SECRET_KEY derivation | `production.py` | Предсказуемость при известном project id | Always set strong SECRET_KEY env |

### Medium

| ID | Суть |
|----|------|
| CSA-M1 | `/health/` leaks exception strings (`config/views.py`) |
| CSA-M2 | Bonus admin API `IsStaff` only (no group) |
| CSA-M3 | JWT localStorage mode XSS impact |
| CSA-M4 | CSP unsafe-inline/unsafe-eval |
| CSA-M5 | ONE_C URL no RFC1918 deny (SSRF if enabled + bad URL) |
| CSA-M6 | No container CPU/RAM limits |
| CSA-M7 | Axes proxy count unset → wrong lockout key behind LB |
| CSA-M8 | ringoo_users can PATCH `is_active` (intentional?) — review policy |

### Low / Informational

Mutable image tags; HSTS preload aggressiveness; social placeholder URLs; incomplete admin action audit coverage; npm transitive moderate advisories.

### Positive (PASS with evidence)

| ID | Контроль | Evidence |
|----|----------|----------|
| CSA-P1 | Argon2 passwords | settings |
| CSA-P2 | Client cannot set paid | payment_security tests **passed** |
| CSA-P3 | Callback token required when Sber on in prod | production.py + tests |
| CSA-P4 | Staff cannot assign is_staff/groups | UserAdminUpdateSerializer |
| CSA-P5 | Non-root prod containers | Dockerfiles USER |
| CSA-P6 | .env not tracked | git ls-files + gitignore |
| CSA-P7 | Admin API not AllowAny | permissions.py |

---

## 20. Непроверенные зоны

1. Реальный VPS: SSH, firewall, Docker daemon exposure, listening ports from Internet.  
2. `pg_hba.conf`, PostgreSQL TLS, role grants на живой БД.  
3. Содержимое локальных `.env` / `.env.development` (намеренно не читались в отчёт).  
4. Полный history secret scan (gitleaks).  
5. Trivy image scan, Bandit, Semgrep.  
6. Live TLS grade / certificate chain.  
7. Backup existence, encryption, offsite copy, restore time.  
8. WAF/CDN/DDoS provider.  
9. Физический/логический pentest admin login.  
10. Concurrent payment races on real Postgres (`test_concurrency_postgres` — отдельная DB).  
11. Browser XSS with real CSP headers from deployed site.

---

## 21. Рейтинг общего риска

| Среда | Риск |
|-------|------|
| Локальный Docker Desktop за NAT | Средний (порты на localhost) |
| VPS с `docker compose up` «как в README» без hardening | **Критический** |
| VPS после обязательных мер разд. 22 + integrations OFF | **Умеренный** (приемлемо для публичной витрины) |

---

## 22. Обязательные исправления до публичного доступа

1. **Не публиковать** Postgres/Redis; использовать `docker-compose.no-host-db-redis-ports.yml` (+ firewall deny).  
2. Сильные уникальные `DB_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY` (≥48), `DEBUG=False`.  
3. **Не** подключать `backend/.env.development` к production-процессу; отдельный prod env.  
4. Least-privilege DB user (не superuser).  
5. Reverse proxy TLS + `SECURE_PROXY_SSL_HEADER` + CSRF/CORS https origins.  
6. `ADMIN_OTP_ENABLED=1` для всех staff/superuser; сменить `DJANGO_ADMIN_URL`; сильные пароли.  
7. `SBER_*=off`, `ONE_C_*=off`; скрыть онлайн-оплату в UI.  
8. Encrypted offsite backups + documented restore.  
9. Убрать/ограничить информативность `/health/` для публичного Internet (или auth/network restrict).  
10. Smoke: с внешней сети порты 5432/5436/6379/6380 **закрыты**.

---

## 23. План повторной проверки

1. После hardened compose: внешний port scan + доказательство закрытых DB/Redis.  
2. `manage.py check --deploy` внутри prod-образа.  
3. Повтор `pytest` payment_security + admin_integrity.  
4. Включить OTP и проверить невозможность admin без второго фактора.  
5. gitleaks/trufflehog по history; Trivy images.  
6. Restore drill backup на пустой staging DB.  
7. Опционально: внешний pentest (отдельный договор).

---

## 24. Финальный вердикт и ответы допуска

### Статус: **SECURITY CONDITIONAL**

Не **SECURITY BLOCKED** по факту «дыры в коде admin без пароля», но **запрещён** наивный публичный deploy текущим default compose.

Не **SECURITY REVIEW PASSED** — Critical infra findings + непроверенный сервер/backup.

### Ответы (разд. 20 задания)

1. **Неавторизованный доступ к admin?** — **Не подтверждён** в коде. Требуется auth; MFA по умолчанию выкл.  
2. **PostgreSQL извне?** — **При default compose — да, порт публикуется** (код конфиг). На реальном firewall — **не проверено**.  
3. **Redis извне?** — **Аналогично — публикуется**; без пароля при пустом env.  
4. **PII без авторизации?** — Полный список пользователей — нет. Чужой заказ — только с секретом (номер+телефон или UUID+телефон).  
5. **Секреты в Git/frontend?** — Tracked реальных `.env` **не** найдено; history tooling не гонялся. `NEXT_PUBLIC_*` — не auth secrets.  
6. **Небезопасные password algorithms?** — **Нет**, Argon2.  
7. **Backup защищены?** — **Не проверено / не доказано**.  
8. **Полноценная защита privileged?** — **Частично** (RBAC да, MFA default нет).  
9. **Безопасно на отдельном VPS?** — **Да, после мер §22**.  
10. **Что не удалось?** — См. §20.  
11. **Critical/High блокеры публикации?** — CSA-C1…C4, CSA-H1…H4, H7 как минимум.  
12. **Что исправить до открытия?** — §22.

---

*Аудит независимый. Абсолютная безопасность не гарантируется. Исправления — только после отдельного разрешения владельца.*
