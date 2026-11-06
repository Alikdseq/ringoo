"""Тесты admin backup: права, архив, шифрование, path traversal, токен."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.backups.models import BackupArchive
from apps.backups.services import (
    BACKUP_LOCK_KEY,
    create_backup_archive,
    decrypt_bytes,
    encrypt_bytes,
    resolve_archive_path,
)

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "backup-tests",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "backup-tests-sessions",
        },
    },
    MEDIA_ROOT=None,  # set in setUp
    BACKUP_STORAGE_ROOT=None,
)
class BackupServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tmp = Path(self._tmp())
        self.media = self.tmp / "media"
        self.media.mkdir(parents=True)
        (self.media / "sample.txt").write_text("hello-media", encoding="utf-8")
        self.store = self.tmp / "backups"
        self.store.mkdir()
        self.superuser = User.objects.create_user(
            phone="+79001112233",
            password="TestPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self._media_override = override_settings(
            MEDIA_ROOT=str(self.media),
            BACKUP_STORAGE_ROOT=str(self.store),
        )
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        cache.clear()

    def _tmp(self):
        import tempfile

        return tempfile.mkdtemp(prefix="ringoo_backup_test_")

    def test_create_archive_contains_media_and_manifest(self):
        archive, token = create_backup_archive(user=self.superuser, password=None)
        self.assertEqual(archive.status, BackupArchive.STATUS_READY)
        self.assertTrue(token)
        path = resolve_archive_path(archive)
        self.assertIsNotNone(path)
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            self.assertIn("manifest.json", names)
            self.assertIn("checksums.txt", names)
            self.assertIn("RESTORE_GUIDE.md", names)
            self.assertTrue(any(n.startswith("media/") for n in names))
            self.assertTrue(any(n.startswith("database/") for n in names))
            self.assertIsNone(zf.testzip())
            # no secrets
            self.assertFalse(any(".env" == Path(n).name and n != ".env.example" for n in names))
            self.assertIn(".env.example", names)

    def test_encrypt_decrypt_roundtrip(self):
        blob = encrypt_bytes(b"zip-bytes-here", "SecretPass1")
        self.assertTrue(blob.startswith(b"RINGOO1"))
        self.assertEqual(decrypt_bytes(blob, "SecretPass1"), b"zip-bytes-here")
        with self.assertRaises(Exception):
            decrypt_bytes(blob, "WrongPass!!")

    def test_encrypted_archive(self):
        archive, _token = create_backup_archive(
            user=self.superuser, password="SecretPass1"
        )
        self.assertTrue(archive.encrypted)
        self.assertTrue(archive.filename.endswith(".enc"))
        path = resolve_archive_path(archive)
        raw = path.read_bytes()
        plain = decrypt_bytes(raw, "SecretPass1")
        with zipfile.ZipFile(io.BytesIO(plain), "r") as zf:
            self.assertIn("manifest.json", zf.namelist())

    def test_restore_drill_extract_media_and_db(self):
        """Изолированный drill: создать → расшифровать → распаковать → проверить media/db."""
        import json
        import shutil
        import tempfile

        archive, _ = create_backup_archive(
            user=self.superuser, password="DrillPass99"
        )
        path = resolve_archive_path(archive)
        plain = decrypt_bytes(path.read_bytes(), "DrillPass99")
        out = Path(tempfile.mkdtemp(prefix="ringoo_restore_out_"))
        try:
            with zipfile.ZipFile(io.BytesIO(plain), "r") as zf:
                self.assertIsNone(zf.testzip())
                zf.extractall(out)
            manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("database", manifest)
            self.assertIn("media", manifest)
            self.assertTrue((out / "media" / "sample.txt").is_file())
            self.assertEqual(
                (out / "media" / "sample.txt").read_text(encoding="utf-8"),
                "hello-media",
            )
            db_files = list((out / "database").iterdir())
            self.assertTrue(db_files)
            media_restored = out / "media_restored"
            shutil.copytree(out / "media", media_restored)
            self.assertTrue((media_restored / "sample.txt").is_file())
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_path_traversal_blocked(self):
        archive, _ = create_backup_archive(user=self.superuser)
        archive.relative_path = "../secrets.txt"
        archive.save(update_fields=["relative_path"])
        self.assertIsNone(resolve_archive_path(archive))

    def test_lock_prevents_parallel(self):
        cache.set(BACKUP_LOCK_KEY, "1", timeout=60)
        with self.assertRaises(RuntimeError):
            create_backup_archive(user=self.superuser)
        cache.delete(BACKUP_LOCK_KEY)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "backup-api-tests",
        },
        "sessions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "backup-api-sessions",
        },
    },
    ADMIN_OTP_ENABLED=False,
)
class BackupAPITests(TestCase):
    def setUp(self):
        cache.clear()
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="ringoo_backup_api_"))
        self.media = self.tmp / "media"
        self.media.mkdir()
        (self.media / "a.bin").write_bytes(b"x")
        self.store = self.tmp / "store"
        self.store.mkdir()
        self.override = override_settings(
            MEDIA_ROOT=str(self.media),
            BACKUP_STORAGE_ROOT=str(self.store),
        )
        self.override.enable()
        self.client = APIClient()
        self.superuser = User.objects.create_user(
            phone="+79001112244",
            password="TestPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.staff = User.objects.create_user(
            phone="+79001112255",
            password="TestPass123!",
            is_staff=True,
            is_superuser=False,
        )

    def tearDown(self):
        self.override.disable()
        cache.clear()

    def test_staff_forbidden(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post("/api/v1/admin/backups/create/", {}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_superuser_create_and_download(self):
        self.client.force_authenticate(user=self.superuser)
        resp = self.client.post("/api/v1/admin/backups/create/", {}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        token = data["download_token"]
        bid = data["id"]
        bad = self.client.get(f"/api/v1/admin/backups/{bid}/download/")
        self.assertEqual(bad.status_code, 403)
        ok = self.client.get(f"/api/v1/admin/backups/{bid}/download/?token={token}")
        self.assertEqual(ok.status_code, 200)
        body = b"".join(ok.streaming_content)
        self.assertTrue(len(body) > 0)
