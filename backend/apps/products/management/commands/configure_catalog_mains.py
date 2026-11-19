"""
Проставляет is_catalog_main на существующих Category по данным 1С.

  python manage.py configure_catalog_mains --dry-run
  python manage.py configure_catalog_mains

Не создаёт Category. Не меняет parent / Product.category.
Пишет только is_catalog_main и catalog_main_sort.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.catalog_mains import MAIN_SECTION_SPECS, MainSectionSpec
from apps.products.models import Category


def _resolve_category(spec: MainSectionSpec) -> tuple[Category | None, str]:
    """
    Возвращает (category|None, status).

    status: matched | missing | ambiguous | skipped_no_node
    """
    if not spec.onec_title and not spec.onec_code and not spec.slug:
        return None, "skipped_no_node"

    if spec.onec_code:
        qs = Category.objects.filter(onec_code=spec.onec_code)
        count = qs.count()
        if count == 1:
            return qs.get(), "matched"
        if count > 1:
            return None, "ambiguous"
        # onec_code задан, но не найден — не fallback на «чужой» title без slug
        if not spec.slug and not spec.onec_title:
            return None, "missing"

    if spec.slug:
        qs = Category.objects.filter(slug=spec.slug)
        count = qs.count()
        if count == 1:
            cat = qs.get()
            # если указан title — сверяем, чтобы slug не указывал на другой узел
            if spec.onec_title and cat.title != spec.onec_title:
                return None, "ambiguous"
            return cat, "matched"
        if count > 1:
            return None, "ambiguous"
        if not spec.onec_title:
            return None, "missing"

    if spec.onec_title:
        qs = Category.objects.filter(title=spec.onec_title)
        count = qs.count()
        if count == 1:
            return qs.get(), "matched"
        if count == 0:
            return None, "missing"
        return None, "ambiguous"

    return None, "missing"


class Command(BaseCommand):
    help = (
        "Пометить существующие узлы Category 1С как главные разделы витрины "
        "(без создания новых категорий и без смены parent/товаров)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только отчёт, без записи.",
        )
        parser.add_argument(
            "--clear-others",
            action="store_true",
            default=True,
            help="Снять is_catalog_main с категорий вне списка (по умолчанию да).",
        )
        parser.add_argument(
            "--no-clear-others",
            action="store_false",
            dest="clear_others",
            help="Не снимать флаг с прочих категорий.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        clear_others = bool(options.get("clear_others"))
        verbosity = int(options.get("verbosity", 1))

        matched: list[dict] = []
        missing: list[dict] = []
        ambiguous: list[dict] = []
        skipped_no_node: list[dict] = []
        found_ids: list = []

        for spec in MAIN_SECTION_SPECS:
            if not spec.onec_title and not spec.onec_code and not spec.slug:
                skipped_no_node.append(
                    {
                        "desired": spec.desired_label,
                        "note": spec.note or "нет узла 1С",
                    }
                )
                continue

            cat, status = _resolve_category(spec)
            if status == "matched" and cat is not None:
                matched.append(
                    {
                        "desired": spec.desired_label,
                        "id": str(cat.id),
                        "title": cat.title,
                        "slug": cat.slug,
                        "onec_code": cat.onec_code,
                        "parent_id": str(cat.parent_id) if cat.parent_id else None,
                        "sort": spec.sort,
                        "note": spec.note,
                    }
                )
                found_ids.append(cat.id)
            elif status == "ambiguous":
                ambiguous.append(
                    {
                        "desired": spec.desired_label,
                        "onec_title": spec.onec_title,
                        "slug": spec.slug,
                        "onec_code": spec.onec_code,
                        "note": "несколько совпадений — пропуск, категории не создаём",
                    }
                )
            elif status == "skipped_no_node":
                skipped_no_node.append(
                    {"desired": spec.desired_label, "note": spec.note or "нет узла 1С"}
                )
            else:
                missing.append(
                    {
                        "desired": spec.desired_label,
                        "onec_title": spec.onec_title,
                        "slug": spec.slug,
                        "onec_code": spec.onec_code,
                        "note": spec.note,
                    }
                )

        if verbosity >= 1:
            self.stdout.write(
                "matched={0} missing={1} ambiguous={2} no_node={3}".format(
                    len(matched),
                    len(missing),
                    len(ambiguous),
                    len(skipped_no_node),
                )
            )
        if verbosity >= 2:
            for row in matched:
                self.stdout.write(
                    "  + {title} id={id} parent_id={parent_id} "
                    "slug={slug} onec={onec_code} ← {desired}".format(**row)
                )
            for row in missing:
                self.stdout.write(
                    self.style.WARNING(
                        "  ! не найдено: {desired} title={onec_title!r} "
                        "slug={slug!r} onec={onec_code!r}".format(**row)
                    )
                )
            for row in ambiguous:
                self.stdout.write(
                    self.style.ERROR(
                        "  !! неоднозначно (пропуск): {desired} "
                        "title={onec_title!r} slug={slug!r}".format(**row)
                    )
                )
            for row in skipped_no_node:
                self.stdout.write(
                    self.style.NOTICE(
                        "  · пропуск (нет узла 1С): {desired} — {note}".format(**row)
                    )
                )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run: изменений нет."))
            return

        with transaction.atomic():
            if clear_others:
                Category.objects.exclude(id__in=found_ids).filter(
                    is_catalog_main=True
                ).update(is_catalog_main=False, catalog_main_sort=0)
            for row in matched:
                Category.objects.filter(id=row["id"]).update(
                    is_catalog_main=True,
                    catalog_main_sort=row["sort"],
                )

        self.stdout.write(self.style.SUCCESS("Главные разделы обновлены."))
