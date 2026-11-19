"""
DTO и статусы Resolver (S1.2.3).

Статусы живут в вычислительном слое и НЕ совпадают 1:1 с choices моделей
ClassificationEvent / UnmatchedProductQueue (модели не меняем на этом этапе).
Маппинг в persist-слой — задача S1.2.4+.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ResolutionStatus(str, Enum):
    MATCH = "match"
    OVERRIDE = "override"
    OVERRIDE_FALLBACK = "override_fallback"
    CONFLICT = "conflict"
    UNMATCHED = "unmatched"
    NEEDS_REVIEW = "needs_review"


class ResolutionSource(str, Enum):
    RULE = "rule"
    LOCKED_OVERRIDE = "locked_override"
    OVERRIDE_FALLBACK = "override_fallback"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class CategoryRef:
    """Целевая витринная категория без ORM."""

    id: str
    is_active: bool
    slug: str = ""


@dataclass(frozen=True, slots=True)
class RuleInput:
    """Активное/кандидатное правило для Resolver и fingerprint (без ORM)."""

    id: str
    code: str
    priority: int
    is_active: bool
    condition_type: str
    condition_payload: dict[str, Any]
    schema_version: int
    target_category: CategoryRef


@dataclass(frozen=True, slots=True)
class OverrideInput:
    """Ручное решение без ORM."""

    category: CategoryRef
    is_locked: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MatchedRuleInfo:
    rule_id: str
    code: str
    priority: int
    category_id: str


@dataclass(frozen=True, slots=True)
class RuleErrorInfo:
    rule_id: str
    code: str
    condition_type: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class SkippedRuleInfo:
    rule_id: str
    code: str
    reason: str


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    status: ResolutionStatus
    category_id: str | None
    winning_rule_id: str | None
    winning_rule_code: str | None
    winning_priority: int | None
    best_priority_matches: tuple[MatchedRuleInfo, ...]
    conflicting_category_ids: tuple[str, ...]
    rule_errors: tuple[RuleErrorInfo, ...]
    skipped_rules: tuple[SkippedRuleInfo, ...]
    source: ResolutionSource
    explanation: str
    fingerprint: str
