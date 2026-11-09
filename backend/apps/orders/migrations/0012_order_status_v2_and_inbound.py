# Generated manually for fulfillment status v2 + 1C inbound journal.

from django.db import migrations, models
import django.db.models.deletion
import uuid


def forwards_status_and_payment(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Payment = apps.get_model("payments", "Payment")

    # Legacy fulfillment → new
    Order.objects.filter(status="confirmed").update(status="processing")
    Order.objects.filter(status="in_progress").update(status="processing")
    Order.objects.filter(status="completed").update(
        status="closed", closure_result="completed"
    )
    Order.objects.filter(status="cancelled").update(
        status="closed", closure_result="cancelled"
    )

    # Backfill payment_status from online Payment rows
    paid_order_ids = (
        Payment.objects.filter(status="paid")
        .values_list("order_id", flat=True)
        .distinct()
    )
    Order.objects.filter(id__in=paid_order_ids).update(payment_status="paid")

    refunded_order_ids = (
        Payment.objects.filter(status="refunded")
        .values_list("order_id", flat=True)
        .distinct()
    )
    Order.objects.filter(id__in=refunded_order_ids).exclude(
        payment_status="paid"
    ).update(payment_status="refunded")

    # Offline already mirrored in onec_paid
    Order.objects.filter(onec_paid=True).exclude(
        payment_status="paid"
    ).update(payment_status="paid")


def backwards_noop(apps, schema_editor):
    # Не возвращаем старые коды автоматически — риск потери closure_result.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_block10_state_sync"),
        ("payments", "0005_block10_state_sync"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="closure_result",
            field=models.CharField(
                blank=True,
                choices=[("completed", "Получен"), ("cancelled", "Отменён")],
                help_text="Заполняется только при status=closed: completed|cancelled",
                max_length=20,
                null=True,
                verbose_name="Результат закрытия",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("unpaid", "Не оплачен"),
                    ("paid", "Оплачен"),
                    ("refunded", "Возвращён"),
                ],
                db_index=True,
                default="unpaid",
                help_text="Независимо от статуса выполнения. Online: ЮKassa; cash/card: 1С.",
                max_length=20,
                verbose_name="Статус оплаты",
            ),
        ),
        migrations.CreateModel(
            name="OneCInboundEvent",
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
                    "event_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        unique=True,
                        verbose_name="ID события 1С",
                    ),
                ),
                (
                    "order_number",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=32,
                        verbose_name="Номер заказа",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("status", "Статус заказа"),
                            ("payment", "Оплата"),
                            ("combined", "Статус и оплата"),
                        ],
                        max_length=20,
                        verbose_name="Тип события",
                    ),
                ),
                (
                    "status_received",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=32,
                        verbose_name="Полученный status",
                    ),
                ),
                (
                    "result_received",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=32,
                        verbose_name="Полученный result",
                    ),
                ),
                (
                    "payment_status_received",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=32,
                        verbose_name="Полученный payment.status",
                    ),
                ),
                (
                    "processing_result",
                    models.CharField(
                        choices=[
                            ("success", "Успех"),
                            ("duplicate", "Дубликат"),
                            ("error", "Ошибка"),
                        ],
                        db_index=True,
                        default="success",
                        max_length=20,
                        verbose_name="Результат обработки",
                    ),
                ),
                ("error_code", models.CharField(blank=True, default="", max_length=64)),
                (
                    "error_message",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "payload_summary",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        verbose_name="Краткое тело (без секретов)",
                    ),
                ),
                ("occurred_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="onec_inbound_events",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Входящее событие 1С",
                "verbose_name_plural": "Входящие события 1С",
                "db_table": "orders_onec_inbound_event",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="onecinboundevent",
            index=models.Index(
                fields=["processing_result", "created_at"],
                name="orders_onec_process_7c1a2b_idx",
            ),
        ),
        migrations.RunPython(forwards_status_and_payment, backwards_noop),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Новый заказ"),
                    ("processing", "В обработке"),
                    ("ready", "Готов"),
                    ("closed", "Завершён"),
                ],
                db_index=True,
                default="new",
                max_length=20,
                verbose_name="Статус выполнения",
            ),
        ),
    ]
