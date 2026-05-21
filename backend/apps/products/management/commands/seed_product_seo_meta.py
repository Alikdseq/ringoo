"""Заполняет meta_title/meta_description для товаров без SEO-полей (первая волна)."""

from django.core.management.base import BaseCommand

from apps.products.models import Product


class Command(BaseCommand):
    help = "Шаблонные meta_title и meta_description для активных товаров без SEO-полей"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Максимум товаров за один запуск (по умолчанию 50)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, без сохранения",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        dry_run = options["dry_run"]
        qs = (
            Product.objects.filter(is_active=True)
            .filter(meta_title__isnull=True)
            .filter(meta_description__isnull=True)
            .order_by("-is_featured", "-created_at")[:limit]
        )
        updated = 0
        for product in qs:
            price = int(product.price) if product.price else None
            meta_title = (
                f"{product.title} купить во Владикавказе"
                + (f" — {price} ₽" if price else "")
            )[:255]
            meta_description = (
                f"{product.title} в наличии в Ringoo. "
                "Официальная гарантия, самовывоз во Владикавказе, доставка по России."
            )[:500]
            self.stdout.write(f"  {product.slug}: {meta_title}")
            if not dry_run:
                product.meta_title = meta_title
                product.meta_description = meta_description
                product.save(update_fields=["meta_title", "meta_description"])
            updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Updated'} {updated} product(s)."
            )
        )
