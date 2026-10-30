"""
Интеграция с 1С:УТ 11 — парсер выгрузок, dry-run импорт каталога, HTTP-клиент.

Импортируйте подмодули явно (parser, importer, client), чтобы не тянуть Django
при простом импорте пакета.
"""

__all__ = [
    "CatalogImportPlan",
    "ImportMode",
    "OneCClient",
    "OneCClientError",
    "plan_catalog_import",
    "write_import_report",
]


def __getattr__(name: str):
    if name in ("OneCClient", "OneCClientError"):
        from .client import OneCClient, OneCClientError

        return {"OneCClient": OneCClient, "OneCClientError": OneCClientError}[name]
    if name in ("CatalogImportPlan", "ImportMode", "plan_catalog_import", "write_import_report"):
        from .importer import (
            CatalogImportPlan,
            ImportMode,
            plan_catalog_import,
            write_import_report,
        )

        return {
            "CatalogImportPlan": CatalogImportPlan,
            "ImportMode": ImportMode,
            "plan_catalog_import": plan_catalog_import,
            "write_import_report": write_import_report,
        }[name]
    raise AttributeError(name)
