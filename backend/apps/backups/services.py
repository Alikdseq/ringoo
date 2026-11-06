"""
Создание полного архива резервной копии: PostgreSQL/SQLite + media + manifest.
Без .env / секретов. Опциональное AES-GCM шифрование паролем администратора.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import shutil
import subprocess
import tempfile
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from apps.backups.models import BackupArchive

logger = logging.getLogger(__name__)

BACKUP_LOCK_KEY = "backups:create_lock"
RESTORE_GUIDE_NAME = "RESTORE_GUIDE.md"
ENC_MAGIC = b"RINGOO1"


def storage_root() -> Path:
    raw = getattr(settings, "BACKUP_STORAGE_ROOT", None)
    if raw:
        root = Path(raw)
    else:
        root = Path(settings.BASE_DIR) / "var" / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_archive_path(archive: BackupArchive) -> Path | None:
    if not archive.relative_path:
        return None
    root = storage_root()
    candidate = (root / archive.relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        logger.error("backup path traversal blocked archive=%s", archive.pk)
        return None
    return candidate if candidate.is_file() else None


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(Path(settings.BASE_DIR).parent),
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode().strip()
    except Exception:
        return ""


def _postgres_version() -> str:
    if connection.vendor != "postgresql":
        return connection.vendor
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            row = cursor.fetchone()
            return str(row[0]) if row else "postgresql"
    except Exception:
        return "postgresql"


def _dump_database(dest: Path) -> dict[str, Any]:
    vendor = connection.vendor
    info: dict[str, Any] = {
        "vendor": vendor,
        "file": dest.name,
        "server_version": _postgres_version(),
    }
    if vendor == "postgresql":
        url = os.getenv("DATABASE_URL", "").strip()
        env = os.environ.copy()
        host = settings.DATABASES["default"].get("HOST") or "127.0.0.1"
        port = str(settings.DATABASES["default"].get("PORT") or "5432")
        name = settings.DATABASES["default"]["NAME"]
        user = settings.DATABASES["default"].get("USER") or "postgres"
        password = settings.DATABASES["default"].get("PASSWORD") or ""
        if url:
            parsed = urlparse(url)
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port:
                port = str(parsed.port)
            if parsed.path:
                name = parsed.path.lstrip("/")
            if parsed.username:
                user = parsed.username
            if parsed.password:
                password = parsed.password
        env["PGPASSWORD"] = password
        cmd = [
            "pg_dump",
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            name,
            "--no-owner",
            "--no-acl",
            "-F",
            "p",
            "-f",
            str(dest),
        ]
        try:
            subprocess.run(
                cmd, check=True, env=env, timeout=600, capture_output=True
            )
            info["format"] = "postgresql_sql"
            return info
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            logger.warning("pg_dump CLI unavailable (%s), trying docker", exc)
            try:
                out = subprocess.check_output(
                    [
                        "docker",
                        "exec",
                        "ringoo_db",
                        "pg_dump",
                        "-U",
                        user,
                        "--no-owner",
                        "--no-acl",
                        name,
                    ],
                    timeout=600,
                    stderr=subprocess.STDOUT,
                )
                dest.write_bytes(out)
                info["format"] = "postgresql_sql_docker"
                return info
            except Exception as docker_exc:
                logger.warning("docker pg_dump failed: %s", docker_exc)
                from django.core.management import call_command

                with dest.open("w", encoding="utf-8") as fh:
                    call_command(
                        "dumpdata",
                        "--natural-foreign",
                        "--natural-primary",
                        stdout=fh,
                    )
                info["format"] = "django_dumpdata"
                info["warning"] = "pg_dump_unavailable_used_dumpdata"
                return info

    db_name = settings.DATABASES["default"]["NAME"]
    if vendor == "sqlite" and db_name and Path(str(db_name)).is_file():
        shutil.copy2(str(db_name), dest)
        info["format"] = "sqlite_copy"
        return info

    from django.core.management import call_command

    with dest.open("w", encoding="utf-8") as fh:
        call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=fh)
    info["format"] = "django_dumpdata"
    return info


def _copy_media(dest_dir: Path) -> dict[str, Any]:
    media = Path(settings.MEDIA_ROOT)
    dest_dir.mkdir(parents=True, exist_ok=True)
    info: dict[str, Any] = {"source": str(media), "copied": False, "files": 0}
    if not media.exists():
        info["warning"] = "media_root_missing"
        return info
    count = 0
    for root, _dirs, files in os.walk(media):
        rel = Path(root).relative_to(media)
        target = dest_dir / rel
        target.mkdir(parents=True, exist_ok=True)
        for name in files:
            shutil.copy2(Path(root) / name, target / name)
            count += 1
    info["copied"] = True
    info["files"] = count
    return info


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def encrypt_bytes(plaintext: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    salt = secrets.token_bytes(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = kdf.derive(password.encode("utf-8"))
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return ENC_MAGIC + salt + nonce + ciphertext


def decrypt_bytes(blob: bytes, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

    if not blob.startswith(ENC_MAGIC):
        raise ValueError("Неизвестный формат зашифрованного архива")
    salt = blob[7:23]
    nonce = blob[23:35]
    ciphertext = blob[35:]
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = kdf.derive(password.encode("utf-8"))
    return AESGCM(key).decrypt(nonce, ciphertext, None)


def _encrypt_file(src: Path, dest: Path, password: str) -> None:
    dest.write_bytes(encrypt_bytes(src.read_bytes(), password))


def _write_payload_tree(work: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    db_dir = work / "database"
    media_dir = work / "media"
    db_dir.mkdir(parents=True, exist_ok=True)
    media_info = _copy_media(media_dir)

    if connection.vendor == "postgresql":
        db_file = db_dir / "ringoo.sql"
    elif connection.vendor == "sqlite":
        db_file = db_dir / "ringoo_db.sqlite3"
    else:
        db_file = db_dir / "ringoo_dumpdata.json"
    db_info = _dump_database(db_file)

    embedded = Path(__file__).with_name("RESTORE_GUIDE_EMBEDDED.md")
    guide_text = (
        embedded.read_text(encoding="utf-8")
        if embedded.exists()
        else "# Восстановление\n\nСм. docs/ops/BACKUP_RESTORE_GUIDE.md\n"
    )
    (work / RESTORE_GUIDE_NAME).write_text(guide_text, encoding="utf-8")

    example_src = Path(settings.BASE_DIR).parent / ".env.example"
    env_example = work / ".env.example"
    if example_src.is_file():
        shutil.copy2(example_src, env_example)
    else:
        env_example.write_text(
            "# Copy and fill secrets locally. Do not commit.\n"
            "SECRET_KEY=\nDATABASE_URL=\nREDIS_URL=\n",
            encoding="utf-8",
        )
    return db_info, media_info


def create_backup_archive(
    *,
    user,
    password: str | None = None,
) -> tuple[BackupArchive, str]:
    """
    Создаёт архив синхронно. Возвращает (archive, plaintext_download_token).
    Пароль не сохраняется. Один активный create — через cache lock.
    """
    ttl_hours = int(getattr(settings, "BACKUP_DOWNLOAD_TTL_HOURS", 24) or 24)
    lock_ttl = int(getattr(settings, "BACKUP_CREATE_LOCK_TTL_SECONDS", 900) or 900)
    if not cache.add(BACKUP_LOCK_KEY, "1", timeout=lock_ttl):
        raise RuntimeError("Создание резервной копии уже выполняется. Подождите.")

    archive = BackupArchive.objects.create(
        created_by=user if getattr(user, "is_authenticated", False) else None,
        status=BackupArchive.STATUS_RUNNING,
        expires_at=timezone.now() + timedelta(hours=ttl_hours),
    )
    download_token = secrets.token_urlsafe(32)
    archive.download_token_hash = hashlib.sha256(download_token.encode()).hexdigest()
    archive.save(update_fields=["download_token_hash", "updated_at"])

    work = Path(tempfile.mkdtemp(prefix="ringoo_backup_"))
    try:
        db_info, media_info = _write_payload_tree(work)

        stamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = f"ringoo_backup_{stamp}"
        plain_zip = work / f"{base_name}.zip"

        components: list[dict[str, Any]] = []
        checksum_lines: list[str] = []
        with zipfile.ZipFile(plain_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(work.rglob("*")):
                if not path.is_file() or path == plain_zip:
                    continue
                arc = path.relative_to(work).as_posix()
                if arc.endswith(".zip"):
                    continue
                zf.write(path, arcname=arc)
                digest = _sha256_file(path)
                checksum_lines.append(f"{digest}  {arc}")
                components.append(
                    {"path": arc, "size": path.stat().st_size, "sha256": digest}
                )

            manifest = {
                "created_at": timezone.now().isoformat(),
                "app_git_commit": _git_commit(),
                "database": db_info,
                "media": media_info,
                "components": components,
                "encrypted": bool(password),
                "archive_id": str(archive.pk),
                "integrity": "checksums.txt listed below; verify after extract",
                "notes": [
                    "Secrets (.env) are NOT included.",
                    "Store this archive on an offline medium.",
                    "Password (if any) is never stored on the server.",
                ],
            }
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            zf.writestr("checksums.txt", "\n".join(checksum_lines) + "\n")

        # Verify zip opens
        with zipfile.ZipFile(plain_zip, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise RuntimeError(f"Архив повреждён: {bad}")

        encrypted = False
        final_name = f"{base_name}.zip"
        out_path = storage_root() / f"{archive.pk}_{final_name}"
        if password:
            enc_name = f"{base_name}.zip.enc"
            enc_path = storage_root() / f"{archive.pk}_{enc_name}"
            _encrypt_file(plain_zip, enc_path, password)
            out_path = enc_path
            final_name = enc_name
            encrypted = True
        else:
            shutil.copy2(plain_zip, out_path)

        sha = _sha256_file(out_path)
        archive.filename = final_name
        archive.relative_path = out_path.name
        archive.size_bytes = out_path.stat().st_size
        archive.sha256 = sha
        archive.encrypted = encrypted
        archive.manifest = {
            "created_at": timezone.now().isoformat(),
            "app_git_commit": _git_commit(),
            "database": db_info,
            "media": media_info,
            "size_bytes": archive.size_bytes,
            "sha256": sha,
            "encrypted": encrypted,
            "zip_test": "ok",
        }
        archive.status = BackupArchive.STATUS_READY
        archive.error_message = ""
        archive.save()
        return archive, download_token
    except Exception as exc:
        logger.exception("backup create failed archive=%s", archive.pk)
        archive.status = BackupArchive.STATUS_FAILED
        archive.error_message = str(exc)[:512]
        archive.save(update_fields=["status", "error_message", "updated_at"])
        raise
    finally:
        cache.delete(BACKUP_LOCK_KEY)
        shutil.rmtree(work, ignore_errors=True)


def verify_download_token(archive: BackupArchive, token: str) -> bool:
    if not token or not archive.download_token_hash:
        return False
    digest = hashlib.sha256(token.encode()).hexdigest()
    return secrets.compare_digest(digest, archive.download_token_hash)


def expire_old_archives() -> int:
    now = timezone.now()
    n = 0
    qs = BackupArchive.objects.filter(
        status=BackupArchive.STATUS_READY,
        expires_at__lt=now,
    )
    for arch in qs.iterator():
        path = resolve_archive_path(arch)
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                logger.warning("failed to delete expired backup %s", arch.pk)
        arch.status = BackupArchive.STATUS_EXPIRED
        arch.relative_path = ""
        arch.download_token_hash = ""
        arch.save(
            update_fields=[
                "status",
                "relative_path",
                "download_token_hash",
                "updated_at",
            ]
        )
        n += 1
    return n
