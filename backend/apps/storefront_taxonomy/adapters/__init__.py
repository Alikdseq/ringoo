"""
ORM Adapter: Django-модели → DTO Resolver/Fingerprint (S1.2.4.1).

Не принимает решений о классификации и не пишет в БД.
"""

from apps.storefront_taxonomy.adapters.orm import (
    AdapterError,
    ClassificationInputBundle,
    build_category_paths,
    load_classification_bundle,
    load_overrides_for_products,
    load_rules,
    product_to_features,
    rule_to_input,
    storefront_category_to_ref,
)

__all__ = [
    "AdapterError",
    "ClassificationInputBundle",
    "build_category_paths",
    "load_classification_bundle",
    "load_overrides_for_products",
    "load_rules",
    "product_to_features",
    "rule_to_input",
    "storefront_category_to_ref",
]
