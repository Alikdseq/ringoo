# RELEASE 46.1 Stage D.2.3: execution_token + stuck applying diagnostics.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0010_onec_catalog_import_plan"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="onecatalogimportplan",
            name="applying_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="onecatalogimportplan",
            name="execution_token",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="onecatalogimportplan",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="onecatalogimportplan",
            name="resolution_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="onecatalogimportplan",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="onec_catalog_plan_resolutions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
