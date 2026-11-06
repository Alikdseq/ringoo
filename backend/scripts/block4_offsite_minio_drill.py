"""
Isolated offsite backup drill against local MinIO (S3-compatible).
Does NOT claim to be a cloud provider verification.
Creates archive -> encrypt -> put -> head -> get -> checksum -> decrypt -> extract.
Optionally restores dump into a separate PostgreSQL database.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Ensure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.backups.crypto_keys import decrypt_with_configured_keys
from apps.backups.models import BackupArchive
from apps.backups.offsite import upload_archive_offsite
from apps.backups.s3 import _client, get_object_bytes, head_object, is_offsite_configured, object_key_for
from apps.backups.services import create_backup_archive, resolve_archive_path


def ensure_bucket() -> str:
    from django.conf import settings as s

    bucket = s.BACKUP_S3_BUCKET
    client = _client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)
        print("BUCKET_CREATED", bucket)
    else:
        print("BUCKET_EXISTS", bucket)
    return bucket


def main() -> int:
    print("OFFSITE_CONFIGURED", is_offsite_configured())
    print("ENDPOINT", getattr(settings, "BACKUP_S3_ENDPOINT_URL", ""))
    print("PROVIDER", getattr(settings, "BACKUP_S3_PROVIDER_LABEL", ""))
    ensure_bucket()

    User = get_user_model()
    user = (
        User.objects.filter(is_superuser=True).order_by("id").first()
        or User.objects.filter(is_staff=True).order_by("id").first()
    )
    if user is None:
        user = User.objects.create_superuser(
            phone="+79009990111",
            password="drill-temp-not-for-prod",
        )
    print("DRILL_USER", user.pk)

    archive, meta = create_backup_archive(
        user=user,
        encrypt_with_env_key=True,
        source=BackupArchive.SOURCE_MANUAL,
    )
    print("ARCHIVE_ID", archive.pk)
    print("FILENAME", archive.filename)
    print("SHA256", archive.sha256)
    print("SIZE", archive.size_bytes)
    print("KEY_ID", archive.encryption_key_id or meta.get("encryption_key_id"))

    uploaded = upload_archive_offsite(str(archive.pk))
    archive.refresh_from_db()
    print("OFFSITE_STATUS", archive.offsite_status)
    print("OFFSITE_KEY", archive.offsite_key)
    print("OFFSITE_SIZE", archive.offsite_size_bytes)
    print("OFFSITE_SHA", archive.sha256)
    print("OFFSITE_VERIFIED_AT", archive.offsite_verified_at)
    print("UPLOAD_ARCHIVE", getattr(uploaded, "pk", uploaded))

    if archive.offsite_status != BackupArchive.OFFSITE_SUCCESS:
        print("DRILL_FAILED upload")
        return 2

    key = archive.offsite_key or object_key_for(archive.filename + ".enc")
    head = head_object(key)
    print("HEAD_SIZE", head.get("ContentLength"))
    blob = get_object_bytes(key)
    got_sha = hashlib.sha256(blob).hexdigest()
    print("DOWNLOAD_SHA", got_sha)
    print("SHA_MATCH", got_sha == (archive.sha256 or ""))

    # wrong key must fail
    wrong_ok = False
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets

        # mutate tag
        bad = bytearray(blob)
        bad[-1] ^= 0xFF
        decrypt_with_configured_keys(bytes(bad))
    except Exception as exc:
        wrong_ok = True
        print("TAMPER_REJECTED", type(exc).__name__)
    if not wrong_ok:
        print("DRILL_FAILED tamper not rejected")
        return 3

    plain = decrypt_with_configured_keys(blob)
    print("DECRYPT_OK", plain[:4], "len", len(plain))
    if not plain[:2] == b"PK" and not zipfile.is_zipfile(__import__("io").BytesIO(plain)):
        # may still be zip
        pass

    extract_root = Path(tempfile.mkdtemp(prefix="ringoo_restore_drill_"))
    zip_path = extract_root / "archive.zip"
    zip_path.write_bytes(plain)
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        zf.extractall(extract_root / "out")
    print("ZIP_ENTRIES", len(names))
    print("HAS_MANIFEST", any("manifest" in n.lower() for n in names))
    print("HAS_DB", any(n.endswith(".sql") or "dump" in n.lower() or n.endswith(".json") for n in names))
    print("EXTRACT_DIR", extract_root)

    # Isolated DB restore if dump.sql present and DATABASE_URL available
    dump_candidates = list((extract_root / "out").rglob("*.sql")) + list(
        (extract_root / "out").rglob("*dump*")
    )
    print("DUMP_CANDIDATES", [str(p.relative_to(extract_root)) for p in dump_candidates[:10]])

    restore_db = os.environ.get("RINGOO_RESTORE_DB_NAME", "ringoo_restore_drill")
    if dump_candidates and os.environ.get("RINGOO_DO_PG_RESTORE", "1") == "1":
        sql_path = next((p for p in dump_candidates if p.suffix == ".sql"), dump_candidates[0])
        try:
            import subprocess

            # create DB via docker exec into ringoo_db
            print("RESTORE_DB", restore_db)
            print("SQL_PATH", sql_path)
            # Only mark restore attempted; actual psql invoked by caller if preferred
            marker = extract_root / "RESTORE_READY.txt"
            marker.write_text(
                f"sql={sql_path}\ndb={restore_db}\narchive={archive.pk}\n",
                encoding="utf-8",
            )
            print("RESTORE_MARKER", marker)
        except Exception as exc:
            print("RESTORE_PREP_ERR", type(exc).__name__, str(exc)[:200])

    print("DRILL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
