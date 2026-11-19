"""
Чистый Resolver классификации (S1.2.3).

Без ORM, без записи в БД, без побочных эффектов.
Использует match_condition / ConditionError из S1.2.2.

Риск ReDoS: Resolver не добавляет timeout; опасный regex в правиле
может замедлить evaluate этого правила (см. отчёт S1.2.2/S1.2.3).
"""

from __future__ import annotations

from typing import Sequence

from apps.storefront_taxonomy.engine.conditions import match_condition
from apps.storefront_taxonomy.engine.errors import ConditionError
from apps.storefront_taxonomy.engine.fingerprint import classification_fingerprint
from apps.storefront_taxonomy.engine.normalizers import (
    NORMALIZER_VERSION,
    NormalizedFeatures,
    ProductFeatures,
)
from apps.storefront_taxonomy.engine.resolution_types import (
    MatchedRuleInfo,
    OverrideInput,
    ResolutionResult,
    ResolutionSource,
    ResolutionStatus,
    RuleErrorInfo,
    RuleInput,
    SkippedRuleInfo,
)


def _safe_error_message(exc: BaseException, *, limit: int = 240) -> str:
    text = f"{type(exc).__name__}: {exc}"
    text = text.replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _eval_rules(
    features: ProductFeatures,
    rules: Sequence[RuleInput],
) -> tuple[
    list[RuleInput],
    list[RuleErrorInfo],
    list[SkippedRuleInfo],
]:
    """
    Возвращает (matched_active_target, rule_errors, skipped).
    Неактивные правила пропускаются в skipped.
    Неактивная целевая категория → skipped, не match.
    ConditionError → rule_errors, без фиктивного match.
    """
    matched: list[RuleInput] = []
    errors: list[RuleErrorInfo] = []
    skipped: list[SkippedRuleInfo] = []

    ordered = sorted(rules, key=lambda r: (r.priority, r.code, r.id))
    for rule in ordered:
        if not rule.is_active:
            skipped.append(
                SkippedRuleInfo(
                    rule_id=rule.id,
                    code=rule.code,
                    reason="inactive_rule",
                )
            )
            continue
        if not rule.target_category.is_active:
            skipped.append(
                SkippedRuleInfo(
                    rule_id=rule.id,
                    code=rule.code,
                    reason="inactive_target_category",
                )
            )
            continue
        try:
            ok = match_condition(
                rule.condition_type,
                rule.condition_payload,
                features,
                schema_version=rule.schema_version,
            )
        except ConditionError as exc:
            errors.append(
                RuleErrorInfo(
                    rule_id=rule.id,
                    code=rule.code,
                    condition_type=rule.condition_type,
                    error_type=type(exc).__name__,
                    message=_safe_error_message(exc),
                )
            )
            continue
        if ok:
            matched.append(rule)

    # Детерминированная диагностика
    errors.sort(key=lambda e: (e.code, e.rule_id, e.error_type))
    skipped.sort(key=lambda s: (s.code, s.rule_id, s.reason))
    return matched, errors, skipped


def _matched_infos(rules: Sequence[RuleInput]) -> tuple[MatchedRuleInfo, ...]:
    infos = [
        MatchedRuleInfo(
            rule_id=r.id,
            code=r.code,
            priority=r.priority,
            category_id=r.target_category.id,
        )
        for r in rules
    ]
    infos.sort(key=lambda m: (m.priority, m.code, m.rule_id))
    return tuple(infos)


def _result(
    *,
    status: ResolutionStatus,
    category_id: str | None,
    winning_rule: RuleInput | None,
    best_matches: Sequence[RuleInput],
    conflicting_category_ids: Sequence[str],
    rule_errors: Sequence[RuleErrorInfo],
    skipped_rules: Sequence[SkippedRuleInfo],
    source: ResolutionSource,
    explanation: str,
    fingerprint: str,
) -> ResolutionResult:
    return ResolutionResult(
        status=status,
        category_id=category_id,
        winning_rule_id=winning_rule.id if winning_rule else None,
        winning_rule_code=winning_rule.code if winning_rule else None,
        winning_priority=winning_rule.priority if winning_rule else None,
        best_priority_matches=_matched_infos(best_matches),
        conflicting_category_ids=tuple(sorted(set(conflicting_category_ids))),
        rule_errors=tuple(rule_errors),
        skipped_rules=tuple(skipped_rules),
        source=source,
        explanation=explanation,
        fingerprint=fingerprint,
    )


def resolve(
    features: ProductFeatures | NormalizedFeatures,
    rules: Sequence[RuleInput],
    override: OverrideInput | None = None,
    *,
    normalizer_version: int | None = None,
    fingerprint: str | None = None,
) -> ResolutionResult:
    """
    Детерминированное разрешение классификации.

    Приоритет: меньшее число priority = выше приоритет.
    Среди совпадений лучшего приоритета: одна категория → MATCH,
    несколько → CONFLICT (низкий приоритет не маскирует).

    Публичный контракт resolve(features, rules, override=None) без изменений.
    Опциональный kw-only fingerprint: готовый classification fingerprint
    (Classifier / batch), без повторного ruleset/features fingerprint.
    features может быть ProductFeatures или уже NormalizedFeatures
    (избегает повторной normalize в match_condition).
    """
    ver = NORMALIZER_VERSION if normalizer_version is None else normalizer_version
    if fingerprint is not None:
        fp = fingerprint
    else:
        fp = classification_fingerprint(
            features,
            rules,
            normalizer_version=ver,
        )

    # 1–3. Locked override
    if override is not None and override.is_locked:
        if override.category.is_active:
            return _result(
                status=ResolutionStatus.OVERRIDE,
                category_id=override.category.id,
                winning_rule=None,
                best_matches=(),
                conflicting_category_ids=(),
                rule_errors=(),
                skipped_rules=(),
                source=ResolutionSource.LOCKED_OVERRIDE,
                explanation=(
                    "Заблокированный override назначает активную витринную категорию."
                ),
                fingerprint=fp,
            )
        return _result(
            status=ResolutionStatus.NEEDS_REVIEW,
            category_id=None,
            winning_rule=None,
            best_matches=(),
            conflicting_category_ids=(),
            rule_errors=(),
            skipped_rules=(),
            source=ResolutionSource.NONE,
            explanation=(
                "Заблокированный override указывает на неактивную витринную категорию; "
                "требуется ручная проверка."
            ),
            fingerprint=fp,
        )

    matched, rule_errors, skipped = _eval_rules(features, rules)

    if matched:
        best_priority = min(r.priority for r in matched)
        top = [r for r in matched if r.priority == best_priority]
        top.sort(key=lambda r: (r.code, r.id))
        category_ids = {r.target_category.id for r in top}

        if len(category_ids) == 1:
            winner = top[0]
            return _result(
                status=ResolutionStatus.MATCH,
                category_id=winner.target_category.id,
                winning_rule=winner,
                best_matches=top,
                conflicting_category_ids=(),
                rule_errors=rule_errors,
                skipped_rules=skipped,
                source=ResolutionSource.RULE,
                explanation=(
                    f"Однозначное совпадение правил с priority={best_priority} "
                    f"(code={winner.code})."
                ),
                fingerprint=fp,
            )

        # CONFLICT — unlocked override не скрывает
        return _result(
            status=ResolutionStatus.CONFLICT,
            category_id=None,
            winning_rule=None,
            best_matches=top,
            conflicting_category_ids=sorted(category_ids),
            rule_errors=rule_errors,
            skipped_rules=skipped,
            source=ResolutionSource.NONE,
            explanation=(
                f"Конфликт: {len(top)} правил с priority={best_priority} "
                f"указывают на разные категории."
            ),
            fingerprint=fp,
        )

    # Нет совпадений — unlocked override fallback
    if override is not None and not override.is_locked:
        if override.category.is_active:
            return _result(
                status=ResolutionStatus.OVERRIDE_FALLBACK,
                category_id=override.category.id,
                winning_rule=None,
                best_matches=(),
                conflicting_category_ids=(),
                rule_errors=rule_errors,
                skipped_rules=skipped,
                source=ResolutionSource.OVERRIDE_FALLBACK,
                explanation=(
                    "Правила не совпали; применён незаблокированный override "
                    "как fallback."
                ),
                fingerprint=fp,
            )
        return _result(
            status=ResolutionStatus.NEEDS_REVIEW,
            category_id=None,
            winning_rule=None,
            best_matches=(),
            conflicting_category_ids=(),
            rule_errors=rule_errors,
            skipped_rules=skipped,
            source=ResolutionSource.NONE,
            explanation=(
                "Нет совпадений правил; незаблокированный override указывает "
                "на неактивную категорию — требуется ручная проверка."
            ),
            fingerprint=fp,
        )

    return _result(
        status=ResolutionStatus.UNMATCHED,
        category_id=None,
        winning_rule=None,
        best_matches=(),
        conflicting_category_ids=(),
        rule_errors=rule_errors,
        skipped_rules=skipped,
        source=ResolutionSource.NONE,
        explanation="Нет совпавших правил и нет применимого override.",
        fingerprint=fp,
    )
