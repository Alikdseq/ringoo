# Admin MFA (TOTP) — Ringoo

## Что защищено

При `ADMIN_OTP_ENABLED=1` (обязательно в production):

1. **Django Admin HTML** — `OTPAdminSite` + `OTPMiddleware`.
2. **Admin API** `/api/v1/admin/*` — permission `AdminMfaVerified` (JWT claim `admin_mfa=1`).
3. **Next Admin** — `GET /auth/staff-access/` требует тот же claim; UI: `/admin/login` → пароль → TOTP.

Парольный `POST /auth/token/` **никогда** не выдаёт `admin_mfa`.  
`POST /auth/token/refresh/` **не** добавляет claim, если его не было в refresh.

Покупатели (не staff) не затрагиваются.

## Первичный enrollment (первый суперпользователь)

На VPS / в контейнере web (после createsuperuser):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py shell -c "
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice
U = get_user_model()
u = U.objects.filter(is_superuser=True).first()
assert u, 'no superuser'
d, created = TOTPDevice.objects.get_or_create(user=u, name='default', defaults={'confirmed': True})
print('user', u.phone, 'device_id', d.id, 'created', created)
print('Scan QR via Django Admin OTP setup or use d.config_url in a secure channel once')
print(d.config_url)
"
```

Отсканируйте `config_url` в Google Authenticator / Aegis **один раз**, затем удалите вывод из истории терминала.

Альтернатива: войти в Django Admin после создания device через UI django-otp (если доступен).

## Ежедневный вход в Next Admin

1. Телефон + пароль.
2. Код TOTP.
3. Сервер выдаёт новые JWT с `admin_mfa=1`.

## Recovery (контролируемое)

**Запрещено:** recovery только по телефону, публичный reset MFA, коды в логах.

Процедура:

1. Доступ к VPS по SSH-ключу (владелец).
2. Бэкап БД.
3. Удалить TOTP devices пользователя в shell (audit вручную).
4. Создать новое устройство.
5. Записать действие в `AuditLog` / ops-журнал.

Не создавайте shared bypass-secret.

## Статус

| Шаг | Статус |
|-----|--------|
| Серверный gate + тесты | VERIFIED локально |
| Enrollment конкретного админа на VPS | **требует ручного действия** |
