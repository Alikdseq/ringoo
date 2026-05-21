# TOTP (2FA) для Django admin

Включение: в окружении задайте `ADMIN_OTP_ENABLED=1`, установите зависимости (`django-otp`, `qrcode`), выполните `python manage.py migrate`.

1. Войдите в админку под staff/superuser (пароль).
2. Раздел **OTP_TOTP** → **TOTP devices** → добавьте устройство для своей учётной записи (QR в приложении-аутhenticator).
3. При следующем входе в `/admin/` потребуется одноразовый код.

Отключение: `ADMIN_OTP_ENABLED=0` (или не задавать).

В тестах (`config.settings.test`) OTP и axes отключены для скорости.
