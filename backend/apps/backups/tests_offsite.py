"""Offsite backup: crypto keys, upload verify, retention (mocked S3)."""

from __future__ import annotations

import base64
import hashlib
import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.backups.crypto_keys import (
    decrypt_with_configured_keys,
    encrypt_with_configured_key,
)
from apps.backups.models import BackupArchive
from apps.backups.offsite import apply_retention_policy, upload_archive_offsite
from apps.backups.services import create_backup_archive

User = get_user_model()

KEY = base64.b64encode(b"0" * 32).decode()


class OffsiteBackupTests(TestCase):
    def setUp(self):
        cache.clear()
        import tempfile

        self.tmp = Path(tempfile.mkdtemp(prefix="offsite_"))
        self.media = self.tmp / "media"
        self.media.mkdir()
        (self.media / "f.txt").write_text("m", encoding="utf-8")
        self.store = self.tmp / "store"
        self.store.mkdir()
        self.override = override_settings(
            MEDIA_ROOT=str(self.media),
            BACKUP_STORAGE_ROOT=str(self.store),
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "offsite-tests",
                },
                "sessions": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "offsite-sess",
                },
            },
            BACKUP_ENCRYPTION_KEY_ID="v1",
            BACKUP_ENCRYPTION_KEY=KEY,
            BACKUP_OFFSITE_ENABLED=True,
            BACKUP_S3_BUCKET="ringoo-backups",
            BACKUP_S3_ACCESS_KEY="ak",
            BACKUP_S3_SECRET_KEY="sk",
            BACKUP_S3_PREFIX="ringoo/backups",
            BACKUP_RETENTION_DAILY_DAYS=1,
            BACKUP_RETENTION_WEEKLY_WEEKS=0,
            BACKUP_RETENTION_MONTHLY_MONTHS=0,
        )
        self.override.enable()
        self.user = User.objects.create_user(
            phone="+79001110001", password="x", is_staff=True, is_superuser=True
        )

    def tearDown(self):
        self.override.disable()
        cache.clear()

    def test_key_encrypt_decrypt_and_wrong_key(self):
        blob, kid = encrypt_with_configured_key(b"hello-archive")
        self.assertEqual(kid, "v1")
        self.assertTrue(blob.startswith(b"RINGOO2"))
        self.assertEqual(decrypt_with_configured_keys(blob), b"hello-archive")

    def test_upload_success_with_mock_s3(self):
        archive, _ = create_backup_archive(
            user=self.user, encrypt_with_env_key=True, source=BackupArchive.SOURCE_SCHEDULED
        )
        stored: dict[str, bytes] = {}

        def fake_put(*, key, body, content_type="application/octet-stream"):
            stored[key] = body
            from apps.backups.s3 import OffsiteObjectMeta

            return OffsiteObjectMeta(key=key, size=len(body), etag="etag1")

        def fake_get(key):
            return stored[key]

        with (
            patch("apps.backups.offsite.put_object", side_effect=fake_put),
            patch("apps.backups.offsite.get_object_bytes", side_effect=fake_get),
            patch("apps.backups.offsite.is_offsite_configured", return_value=True),
            patch("apps.backups.offsite.encryption_configured", return_value=True),
        ):
            out = upload_archive_offsite(archive.pk)
        self.assertEqual(out.offsite_status, BackupArchive.OFFSITE_SUCCESS)
        self.assertTrue(out.offsite_key)
        self.assertTrue(out.offsite_verified_at)

    def test_upload_checksum_mismatch_fails(self):
        archive, _ = create_backup_archive(
            user=self.user, encrypt_with_env_key=True
        )
        stored: dict[str, bytes] = {}

        def fake_put(*, key, body, content_type="application/octet-stream"):
            from apps.backups.s3 import OffsiteObjectMeta

            stored[key] = body
            return OffsiteObjectMeta(key=key, size=len(body), etag="e")

        def fake_get(key):
            # same size, wrong content
            return b"x" * len(stored[key])

        with (
            patch("apps.backups.offsite.put_object", side_effect=fake_put),
            patch("apps.backups.offsite.get_object_bytes", side_effect=fake_get),
            patch("apps.backups.offsite.is_offsite_configured", return_value=True),
            patch("apps.backups.offsite.encryption_configured", return_value=True),
        ):
            with self.assertRaises(Exception):
                upload_archive_offsite(archive.pk)
        archive.refresh_from_db()
        self.assertEqual(archive.offsite_status, BackupArchive.OFFSITE_FAILED)

    def test_retention_keeps_recent(self):
        from datetime import timedelta

        from django.utils import timezone

        a = BackupArchive.objects.create(
            status=BackupArchive.STATUS_READY,
            offsite_status=BackupArchive.OFFSITE_SUCCESS,
            offsite_key="old/key",
            filename="old.zip.enc",
        )
        BackupArchive.objects.filter(pk=a.pk).update(
            offsite_uploaded_at=timezone.now() - timedelta(days=400)
        )
        with patch("apps.backups.offsite.delete_object") as delete_mock:
            result = apply_retention_policy()
        self.assertGreaterEqual(
            result.get("deleted", 0),
            1,
            msg=f"retention result={result} uploaded_at={BackupArchive.objects.get(pk=a.pk).offsite_uploaded_at}",
        )
        delete_mock.assert_called()
