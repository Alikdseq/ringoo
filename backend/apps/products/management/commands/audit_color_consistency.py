"""Отчёт по соответствию slug/label/hex у ProductColor."""

from django.core.management.base import BaseCommand

from apps.products.models import ProductColor
from apps.products.services.public_catalog_flat import guess_hex_for_slug

GRAY_HEX = {"#d4d4d8", "#a3a3a3", "#default", ""}


class Command(BaseCommand):
    help = "Печатает ProductColor с пустым/серым hex или несовпадением label и slug."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Макс. строк в отчёте")

    def handle(self, *args, **options):
        limit = options["limit"]
        issues = []
        for color in ProductColor.objects.filter(is_active=True).select_related("product"):
            hx = (color.hex or "").strip().lower()
            guessed = guess_hex_for_slug(color.slug) or guess_hex_for_slug(
                (color.label or "").lower().replace(" ", "-")
            )
            problems = []
            if not hx or hx in GRAY_HEX:
                problems.append("hex_empty_or_gray")
            elif guessed and hx != guessed.lower():
                problems.append(f"hex_mismatch(api={hx}, guess={guessed})")
            label_key = (color.label or "").lower().replace(" ", "-")
            if color.slug and label_key and color.slug not in label_key and label_key not in color.slug:
                if not any(
                    tok in label_key
                    for tok in color.slug.replace("-", " ").split()
                    if len(tok) > 2
                ):
                    problems.append("label_slug_drift")
            if problems:
                issues.append(
                    (color.product.title, color.slug, color.label, color.hex, "; ".join(problems))
                )
        self.stdout.write(f"Проверено активных оттенков: {ProductColor.objects.filter(is_active=True).count()}")
        self.stdout.write(f"Замечаний: {len(issues)}")
        for row in issues[:limit]:
            self.stdout.write(f"  • {row[0]} | {row[1]} | {row[2]!r} | {row[3]!r} | {row[4]}")
        if len(issues) > limit:
            self.stdout.write(f"  … и ещё {len(issues) - limit}")
