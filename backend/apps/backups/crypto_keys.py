"""
Шифрование архивов ключом из окружения (автоматические offsite-копии).

Формат: RINGOO2 | key_id_len(1) | key_id | nonce(12) | AES-256-GCM ciphertext
Парольный формат RINGOO1 (Scrypt) остаётся для ручных скачиваний.
"""

from __future__ import annotations

import base64
import logging
import secrets
from typing import Mapping

from django.conf import settings

logger = logging.getLogger(__name__)

ENC_MAGIC_KEY = b"RINGOO2"


def _decode_key_material(raw: str) -> bytes:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Пустой ключ шифрования")
    # accept base64 or hex
    try:
        key = base64.b64decode(value, validate=True)
    except Exception:
        key = bytes.fromhex(value)
    if len(key) != 32:
        raise ValueError("BACKUP_ENCRYPTION_KEY должен быть 32 байта (AES-256)")
    return key


def configured_keys() -> dict[str, bytes]:
    """
    Активный + предыдущие ключи для ротации.
    BACKUP_ENCRYPTION_KEY_ID + BACKUP_ENCRYPTION_KEY
    BACKUP_ENCRYPTION_KEYS_PREVIOUS = "id1:b64,id2:b64"
    """
    out: dict[str, bytes] = {}
    active_id = str(getattr(settings, "BACKUP_ENCRYPTION_KEY_ID", "") or "").strip()
    active_key = str(getattr(settings, "BACKUP_ENCRYPTION_KEY", "") or "").strip()
    if active_id and active_key:
        out[active_id] = _decode_key_material(active_key)
    prev = str(getattr(settings, "BACKUP_ENCRYPTION_KEYS_PREVIOUS", "") or "").strip()
    if prev:
        for part in prev.split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            kid, material = part.split(":", 1)
            kid = kid.strip()
            if not kid:
                continue
            try:
                out[kid] = _decode_key_material(material.strip())
            except ValueError:
                logger.warning("skip invalid previous backup encryption key id=%s", kid)
    return out


def encryption_configured() -> bool:
    keys = configured_keys()
    active_id = str(getattr(settings, "BACKUP_ENCRYPTION_KEY_ID", "") or "").strip()
    return bool(active_id and active_id in keys)


def encrypt_with_configured_key(plaintext: bytes) -> tuple[bytes, str]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    keys = configured_keys()
    active_id = str(getattr(settings, "BACKUP_ENCRYPTION_KEY_ID", "") or "").strip()
    if not active_id or active_id not in keys:
        raise RuntimeError(
            "Автоматическое шифрование не настроено "
            "(BACKUP_ENCRYPTION_KEY_ID / BACKUP_ENCRYPTION_KEY)."
        )
    key_id_b = active_id.encode("utf-8")
    if len(key_id_b) > 255:
        raise ValueError("BACKUP_ENCRYPTION_KEY_ID слишком длинный")
    nonce = secrets.token_bytes(12)
    ct = AESGCM(keys[active_id]).encrypt(nonce, plaintext, None)
    blob = ENC_MAGIC_KEY + bytes([len(key_id_b)]) + key_id_b + nonce + ct
    return blob, active_id


def decrypt_with_configured_keys(blob: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not blob.startswith(ENC_MAGIC_KEY):
        raise ValueError("Ожидался формат RINGOO2 (ключевое шифрование)")
    kid_len = blob[7]
    key_id = blob[8 : 8 + kid_len].decode("utf-8")
    nonce = blob[8 + kid_len : 8 + kid_len + 12]
    ciphertext = blob[8 + kid_len + 12 :]
    keys = configured_keys()
    if key_id not in keys:
        raise ValueError(
            f"Ключ шифрования id={key_id} недоступен. "
            "Добавьте его в BACKUP_ENCRYPTION_KEYS_PREVIOUS — иначе архив невосстановим."
        )
    return AESGCM(keys[key_id]).decrypt(nonce, ciphertext, None)


def key_inventory_public() -> Mapping[str, str]:
    """Публичные метаданные без материала ключа."""
    active_id = str(getattr(settings, "BACKUP_ENCRYPTION_KEY_ID", "") or "").strip()
    return {
        "active_key_id": active_id or "",
        "known_key_ids": sorted(configured_keys().keys()),
        "configured": encryption_configured(),
    }
