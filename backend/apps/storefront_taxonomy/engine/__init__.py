"""
Детерминированный движок классификации (S1.2.x).

S1.2.2: нормализация и conditions.
S1.2.3: resolver + fingerprint (без ORM / Apply).
"""

from apps.storefront_taxonomy.engine.conditions import (
    match_condition,
    validate_condition,
)
from apps.storefront_taxonomy.engine.errors import (
    ConditionError,
    ConditionEvalError,
    ExpressionLimitError,
    InvalidRegexError,
    PayloadSchemaError,
    UnknownConditionTypeError,
    UnsafeRegexError,
    UnsupportedSchemaVersionError,
)
from apps.storefront_taxonomy.engine.fingerprint import (
    classification_fingerprint,
    features_fingerprint,
    ruleset_fingerprint,
)
from apps.storefront_taxonomy.engine.normalizers import (
    NORMALIZER_VERSION,
    NormalizedFeatures,
    ProductFeatures,
    normalize_brand,
    normalize_features,
    normalize_slug,
    normalize_text,
)
from apps.storefront_taxonomy.engine.resolution_types import (
    CategoryRef,
    MatchedRuleInfo,
    OverrideInput,
    ResolutionResult,
    ResolutionSource,
    ResolutionStatus,
    RuleErrorInfo,
    RuleInput,
    SkippedRuleInfo,
)
from apps.storefront_taxonomy.engine.resolver import resolve

__all__ = [
    "NORMALIZER_VERSION",
    "ProductFeatures",
    "NormalizedFeatures",
    "normalize_text",
    "normalize_brand",
    "normalize_slug",
    "normalize_features",
    "validate_condition",
    "match_condition",
    "ConditionError",
    "PayloadSchemaError",
    "UnknownConditionTypeError",
    "InvalidRegexError",
    "UnsafeRegexError",
    "UnsupportedSchemaVersionError",
    "ExpressionLimitError",
    "ConditionEvalError",
    "CategoryRef",
    "RuleInput",
    "OverrideInput",
    "ResolutionStatus",
    "ResolutionSource",
    "MatchedRuleInfo",
    "RuleErrorInfo",
    "SkippedRuleInfo",
    "ResolutionResult",
    "resolve",
    "features_fingerprint",
    "ruleset_fingerprint",
    "classification_fingerprint",
]
