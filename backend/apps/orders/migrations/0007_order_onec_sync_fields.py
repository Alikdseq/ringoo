from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_order_anonymized_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="onec_client_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="UUID контрагента из SiteRegistration/registrate",
                max_length=64,
                verbose_name="ClientId 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_warehouse_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                verbose_name="warehouseId 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_document_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                verbose_name="documentId 1С (текущий)",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_document_number",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                verbose_name="documentNumber 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_document_type",
            field=models.CharField(
                blank=True,
                default="",
                max_length=64,
                verbose_name="documentType 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_order_document_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Сохраняется при первом paid=false; после оплаты текущий — реализация",
                max_length=64,
                verbose_name="documentId ЗаказКлиента",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_paid",
            field=models.BooleanField(
                default=False,
                help_text="Последний успешно принятый признак оплаты документа в 1С",
                verbose_name="paid принят в 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_posted",
            field=models.BooleanField(
                default=False,
                verbose_name="Документ проведён в 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_sync_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pending", "Ожидает отправки"),
                    ("synced", "Заказ в 1С (paid=false)"),
                    ("paid_synced", "Реализация в 1С (paid=true)"),
                    ("cancelled", "Отменён в 1С"),
                    ("error", "Ошибка синхронизации"),
                    ("blocked", "Заблокирован (нет склада/клиента)"),
                    ("disabled", "Синхронизация выключена"),
                    ("pending_review", "Требует сверки с 1С"),
                ],
                db_index=True,
                default="",
                max_length=20,
                verbose_name="Статус синхронизации 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_last_error",
            field=models.CharField(
                blank=True,
                default="",
                max_length=512,
                verbose_name="Последняя ошибка 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_synced_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Последняя успешная синхронизация 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_sync_attempts",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Попыток синхронизации 1С",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_sync_claim",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Защита от параллельных воркеров и устаревших HTTP-ответов",
                max_length=64,
                verbose_name="Токен захвата sync-задачи",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="onec_payload_snapshot",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Исходный запрос (кроме paid) для идемпотентных повторов и перехода paid=true",
                verbose_name="Снимок payload SiteOrders",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="onec_product_code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="productCode для SiteOrders (снимок на момент заказа)",
                max_length=64,
                verbose_name="Код номенклатуры 1С",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="onec_series_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="UUID серии; пусто → в JSON уходит null",
                max_length=64,
                verbose_name="seriesId 1С",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["onec_sync_status"],
                name="orders_orde_onec_sy_7a1c2d_idx",
            ),
        ),
    ]
