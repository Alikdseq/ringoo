"""
Фильтры логирования: снижение утечки ПДн в консоль и файлы (3.1.3).
"""

from __future__ import annotations

import logging
import re

from config.pii import mask_email, mask_phone

# Email в произвольном тексте
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")

# Типичные российские номера в строке (7XXXXXXXXXX, +7…, 8…)
_PHONE_RE = re.compile(
    r"(?:\+?7|8)[\s\-]?(?:\(\s*)?\d{3}(?:\s*\))?"
    r"[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"|\+?\d{11,15}\b"
)


def _redact_emails(text: str) -> str:
    return _EMAIL_RE.sub(lambda m: mask_email(m.group(0)), text)


def _redact_phones(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return mask_phone(match.group(0))

    return _PHONE_RE.sub(repl, text)


def redact_log_message(text: str) -> str:
    if not text or ("@" not in text and not any(c.isdigit() for c in text)):
        return text
    return _redact_phones(_redact_emails(text))


class RedactPIIFilter(logging.Filter):
    """После форматирования записи маскирует email и телефоны в сообщении."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = redact_log_message(msg)
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True
