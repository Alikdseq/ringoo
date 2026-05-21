"""Обновить hex у ProductColor по slug/label (оранж и др.)."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.products.models import ProductColor
from apps.products.services.public_catalog_flat import guess_hex_for_slug

GRAY_HEX = {"#d4d4d8", "#a3a3a3", "#default"}


def _needs_fix(color: ProductColor) -> bool:
    hx = (color.hex or "").strip().lower()
    if not hx:
        return True
    if hx in GRAY_HEX:
        return True
    return False


class Command(BaseCommand):
    help = "Подставить hex оттенкам по slug/label, если пусто или серый fallback."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать изменения, без сохранения",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = ProductColor.objects.filter(is_active=True).filter(
            Q(hex__isnull=True) | Q(hex="") | Q(hex__iexact="#d4d4d8") | Q(hex__iexact="#a3a3a3")
        )
        updated = 0
        for color in qs.iterator():
            if not _needs_fix(color):
                continue
            guessed = guess_hex_for_slug(color.slug)
            if not guessed:
                label_key = (color.label or "").lower().replace(" ", "-")
                guessed = guess_hex_for_slug(label_key)
            if not guessed:
                continue
            self.stdout.write(f"{color.product_id} / {color.slug}: {color.hex!r} -> {guessed}")
            if not dry_run:
                color.hex = guessed
                color.save(update_fields=["hex"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Обновлено: {updated}" + (" (dry-run)" if dry_run else "")))
