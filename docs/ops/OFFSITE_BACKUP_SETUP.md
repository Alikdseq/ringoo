# Внешнее резервное копирование (S3-compatible)

## Назначение

Автоматически сохранять **зашифрованные** полные архивы Ringoo вне VPS (Yandex Object Storage, Selectel, AWS S3, MinIO и т.п.).

Ручное скачивание на компьютер остаётся. Offsite — второй независимый контур.

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `BACKUP_OFFSITE_ENABLED` | `1` включить |
| `BACKUP_S3_ENDPOINT_URL` | Endpoint (для Yandex/Selectel/MinIO) |
| `BACKUP_S3_REGION` | Регион |
| `BACKUP_S3_BUCKET` | Отдельный private bucket |
| `BACKUP_S3_ACCESS_KEY` / `BACKUP_S3_SECRET_KEY` | Credentials **только** для backup |
| `BACKUP_S3_PREFIX` | Например `ringoo/backups` |
| `BACKUP_S3_PROVIDER_LABEL` | Метка в админке |
| `BACKUP_ENCRYPTION_KEY_ID` | ID активного ключа (напр. `v1`) |
| `BACKUP_ENCRYPTION_KEY` | 32 байта в base64 или hex |
| `BACKUP_ENCRYPTION_KEYS_PREVIOUS` | `v0:base64,...` для ротации |
| `BACKUP_SCHEDULED_ENABLED` | Суточный Celery Beat job |
| `BACKUP_RETENTION_*` | Политика хранения |

**Секреты не коммитить.** Ключ шифрования храните отдельно от VPS (менеджер паролей / сейф). Потеря ключа = невозможность расшифровать архивы.

## Права bucket

- Запрет публичного доступа и листинга снаружи.
- App credentials: `PutObject`, `GetObject`, `HeadObject`, `ListBucket` (prefix), по возможности **без Delete** или Delete только на prefix retention job с отдельной ролью.
- Versioning / Object Lock — по возможности у провайдера.

## Проверка

1. Админка → Резервное копирование → «Проверить подключение».
2. Создать архив → «Отправить во внешнее хранилище».
3. «Проверить последнюю копию».
4. Скачать объект из консоли провайдера → расшифровать ключом → сверить checksum → restore по `BACKUP_RESTORE_GUIDE.md` на **новой** тестовой БД.

## Сценарий «VPS потерян»

Нужны: bucket + `BACKUP_ENCRYPTION_KEY*` + этот репозиторий. Скачать объект, расшифровать (`decrypt_with_configured_keys`), восстановить БД/media. Production restore кнопкой админки **не** делается.

## Локальный drill (MinIO) — 2026-11-06

Выполнен на изолированном MinIO (не cloud-провайдер):

1. `BACKUP_OFFSITE_ENABLED=1` + endpoint MinIO + `BACKUP_ENCRYPTION_KEY*`
2. `python scripts/block4_offsite_minio_drill.py` в контейнере `ringoo_backend`
3. Upload → HEAD → GET → SHA256 match → decrypt RINGOO2 → unzip
4. SQL dump восстановлен в БД `ringoo_restore_drill` (отдельно от рабочей)

Cloud Yandex/Selectel/AWS **не** подключался: нет credentials владельца.

## Зависимости Python

Для RINGOO2 нужен пакет `cryptography` (добавлен в `requirements.txt`).
