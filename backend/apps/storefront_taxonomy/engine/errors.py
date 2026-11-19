"""Контролируемые ошибки движка условий (S1.2.2)."""


class ConditionError(Exception):
    """Базовая контролируемая ошибка условия / payload."""


class PayloadSchemaError(ConditionError):
    """Некорректная схема condition_payload."""


class UnknownConditionTypeError(ConditionError):
    """Неизвестный condition_type."""


class InvalidRegexError(ConditionError):
    """Регулярное выражение не компилируется."""


class UnsafeRegexError(ConditionError):
    """Регулярное выражение отклонено fail-closed эвристикой безопасности."""


class UnsupportedSchemaVersionError(ConditionError):
    """schema_version не поддерживается."""


class ExpressionLimitError(ConditionError):
    """Превышена глубина или число узлов composite."""


class ConditionEvalError(ConditionError):
    """Ошибка выполнения условия после валидации схемы."""
