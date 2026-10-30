"""
Импорт каталога из XML-выгрузки 1С или из HTTP API.

По умолчанию — dry-run без записи в БД. Запись только с --apply
и --i-understand-apply. HTTP только при --from-api и ONE_C_API_ENABLED.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from integrations.onec.client import OneCClientError
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    fetch_and_plan_from_api,
    plan_catalog_import,
    write_import_report,
)
from integrations.onec.parser import OneCParseError


class Command(BaseCommand):
    help = (
        "Планирует (dry-run) или применяет импорт категорий/товаров/остатков "
        "из XML выгрузки 1С или HTTP API. По умолчанию ничего не пишет в БД."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--folders",
            default="",
            help="Путь к XML с папками (Иерархия Папок.xml). Не нужен с --from-api.",
        )
        parser.add_argument(
            "--products",
            default="",
            help="Путь к XML с товарами (Товары.xml). Не нужен с --from-api.",
        )
        parser.add_argument(
            "--from-api",
            action="store_true",
            help=(
                "Загрузить XML через GET CatalogFolders/folders и "
                "CatalogProducts/products. Требует ONE_C_API_ENABLED и учётные данные."
            ),
        )
        parser.add_argument(
            "--report",
            default="",
            help="Куда сохранить JSON-отчёт",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Записать изменения в БД. Без флага — только dry-run.",
        )
        parser.add_argument(
            "--i-understand-apply",
            action="store_true",
            help="Обязательное подтверждение для --apply.",
        )

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        from_api = bool(options["from_api"])
        if apply and not options["i_understand_apply"]:
            raise CommandError(
                "Для записи в БД укажите одновременно --apply и --i-understand-apply. "
                "Сначала выполните dry-run и проверьте JSON-отчёт."
            )

        mode = ImportMode.APPLY if apply else ImportMode.DRY_RUN
        self.stdout.write(f"Режим: {mode.value}")

        try:
            if from_api:
                self.stdout.write("Источник: HTTP API 1С (folders → products)")
                plan = fetch_and_plan_from_api(mode=mode)
            else:
                folders = Path(options["folders"] or "")
                products = Path(options["products"] or "")
                if not folders.is_file():
                    raise CommandError(
                        "Укажите --folders и --products или используйте --from-api"
                    )
                if not products.is_file():
                    raise CommandError(f"Файл товаров не найден: {products}")
                plan = plan_catalog_import(folders, products, mode=mode)
        except OneCClientError as exc:
            raise CommandError(f"Ошибка HTTP 1С: {exc}") from exc
        except OneCParseError as exc:
            raise CommandError(
                f"XML не принят, БД не изменена: {exc}"
            ) from exc

        report_path = options["report"]
        if not report_path:
            report_path = str(Path.cwd() / f"onec_import_report_{mode.value}.json")
        out = write_import_report(plan, report_path)

        s = plan.summary
        self.stdout.write(self.style.NOTICE("— Краткий отчёт —"))
        self.stdout.write(f"Источник папок: {plan.source_folders_path}")
        self.stdout.write(f"Источник товаров: {plan.source_products_path}")
        self.stdout.write(f"Папок: {plan.folder_count}")
        self.stdout.write(f"Строк товаров: {plan.product_row_count}")
        self.stdout.write(f"Уникальных кодов: {plan.unique_product_count}")
        self.stdout.write(
            "Категории: "
            f"create={s.get('categories_create')} "
            f"update={s.get('categories_update')} "
            f"skip={s.get('categories_skip')}"
        )
        self.stdout.write(
            "Товары: "
            f"create={s.get('products_create')} "
            f"update={s.get('products_update')} "
            f"skip={s.get('products_skip')} "
            f"ambiguous={s.get('products_ambiguous')}"
        )
        self.stdout.write(
            "Остатки: "
            f"upsert={s.get('stocks_upsert')} "
            f"skip={s.get('stocks_skip')} "
            f"warehouses={s.get('warehouses')}"
        )
        self.stdout.write(
            f"Замечания: {s.get('issues')} "
            f"(в т.ч. серии={s.get('series_rows')}, "
            f"без папки={s.get('missing_category_products')})"
        )
        self.stdout.write(self.style.SUCCESS(f"JSON-отчёт: {out}"))

        if apply:
            result = apply_catalog_import(plan)
            self.stdout.write(self.style.SUCCESS(f"Применено: {result}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run завершён. База не изменена. "
                    "Для записи: --apply --i-understand-apply"
                )
            )
