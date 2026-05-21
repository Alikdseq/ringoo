"""
Маскирование персональных данных в логах (ФИО, телефон, email, адрес не светятся в открытом виде).
"""


def mask_email(email: str | None) -> str:
    """Пример: user@example.com → u***@***.com."""
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local or not domain:
        return "***"
    return f"{local[0]}***@{domain[0]}***.{domain.split('.')[-1] if '.' in domain else '***'}"


def mask_phone(phone: str | None) -> str:
    """Пример: +79991234567 → +79***67."""
    if not phone:
        return "***"
    digits = "".join(c for c in str(phone) if c.isdigit())
    if len(digits) < 4:
        return "***"
    return f"{digits[:2]}***{digits[-2:]}"


def mask_name(name: str | None) -> str:
    """Пример: Иванов Иван Иванович → И***в И***н."""
    if not name or not name.strip():
        return "***"
    parts = name.strip().split()
    return " ".join(
        (p[0] + "***" + p[-1]) if len(p) > 2 else (p[0] + "***") if p else "***"
        for p in parts
    )[:20]
