# Generated manually for store pages and manager profiles

from django.db import migrations, models
import django.db.models.deletion
import uuid

import apps.stores.models


def populate_manager_slugs(apps, schema_editor):
    Manager = apps.get_model("stores", "Manager")
    from django.utils.text import slugify

    for manager in Manager.objects.order_by("pk"):
        if manager.slug:
            continue
        base = slugify(manager.name, allow_unicode=True) or "manager"
        slug = base
        n = 2
        while Manager.objects.filter(slug=slug).exclude(pk=manager.pk).exists():
            slug = f"{base}-{n}"
            n += 1
        manager.slug = slug
        manager.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("stores", "0003_seed_stores_and_managers"),
    ]

    operations = [
        migrations.AddField(
            model_name="store",
            name="description",
            field=models.TextField(blank=True, verbose_name="Описание"),
        ),
        migrations.AddField(
            model_name="store",
            name="meta_title",
            field=models.CharField(blank=True, max_length=255, verbose_name="Meta title"),
        ),
        migrations.AddField(
            model_name="store",
            name="meta_description",
            field=models.CharField(blank=True, max_length=500, verbose_name="Meta description"),
        ),
        migrations.CreateModel(
            name="StoreImage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        upload_to=apps.stores.models.store_image_upload_to,
                        verbose_name="Изображение",
                    ),
                ),
                ("alt_text", models.CharField(blank=True, max_length=255, verbose_name="Alt-текст")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активно")),
                (
                    "store",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="stores.store",
                        verbose_name="Магазин",
                    ),
                ),
            ],
            options={
                "verbose_name": "Изображение магазина",
                "verbose_name_plural": "Изображения магазинов",
                "db_table": "stores_storeimage",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddField(
            model_name="manager",
            name="slug",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Slug"),
        ),
        migrations.AddField(
            model_name="manager",
            name="job_title",
            field=models.CharField(blank=True, max_length=255, verbose_name="Должность"),
        ),
        migrations.AddField(
            model_name="manager",
            name="bio",
            field=models.TextField(blank=True, verbose_name="О себе"),
        ),
        migrations.AddField(
            model_name="manager",
            name="photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=apps.stores.models.manager_photo_upload_to,
                verbose_name="Фото",
            ),
        ),
        migrations.AddField(
            model_name="manager",
            name="photo_2",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=apps.stores.models.manager_photo_upload_to,
                verbose_name="Фото 2",
            ),
        ),
        migrations.AddField(
            model_name="manager",
            name="photo_alt",
            field=models.CharField(blank=True, max_length=255, verbose_name="Alt фото 1"),
        ),
        migrations.AddField(
            model_name="manager",
            name="photo_2_alt",
            field=models.CharField(blank=True, max_length=255, verbose_name="Alt фото 2"),
        ),
        migrations.RunPython(populate_manager_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="manager",
            name="slug",
            field=models.SlugField(max_length=255, unique=True, verbose_name="Slug"),
        ),
    ]
