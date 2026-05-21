# Generated for bonus app: BonusAccount, BonusTransaction (PLAN 2.1.1, 2.1.2)
# Dependencies ordered for safe apply in Docker (users + orders must exist).

from decimal import Decimal

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0001_order_and_orderitem"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BonusAccount",
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
                    "balance",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=12,
                        verbose_name="Баланс",
                    ),
                ),
                (
                    "total_earned",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=12,
                        verbose_name="Всего начислено",
                    ),
                ),
                (
                    "total_spent",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=12,
                        verbose_name="Всего списано",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Дата обновления",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_account",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Бонусный счёт",
                "verbose_name_plural": "Бонусные счета",
                "db_table": "bonus_bonusaccount",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="BonusTransaction",
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
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        verbose_name="Сумма",
                        help_text="Положительная — начисление, отрицательная — списание",
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("order_reward", "Начисление за заказ"),
                            ("order_refund", "Возврат по заказу"),
                            ("admin_adjust", "Корректировка администратором"),
                            ("order_spend", "Списание при заказе"),
                        ],
                        max_length=32,
                        verbose_name="Причина",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        null=True,
                        verbose_name="Описание",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Дата создания",
                    ),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="bonus.bonusaccount",
                        verbose_name="Бонусный счёт",
                    ),
                ),
                (
                    "related_order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="bonus_transactions",
                        to="orders.order",
                        verbose_name="Связанный заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Бонусная транзакция",
                "verbose_name_plural": "Бонусные транзакции",
                "db_table": "bonus_bonustransaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="bonusaccount",
            index=models.Index(fields=["user"], name="bonus_bonus_user_id_8a1f0d_idx"),
        ),
        migrations.AddIndex(
            model_name="bonusaccount",
            index=models.Index(
                fields=["updated_at"], name="bonus_bonus_updated_2c2b2a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="bonustransaction",
            index=models.Index(
                fields=["account"], name="bonus_bonus_account_7e8f3c_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="bonustransaction",
            index=models.Index(
                fields=["created_at"], name="bonus_bonus_created_1d4e5b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="bonustransaction",
            index=models.Index(fields=["reason"], name="bonus_bonus_reason_9a2b3c_idx"),
        ),
        migrations.AddIndex(
            model_name="bonustransaction",
            index=models.Index(
                fields=["related_order"], name="bonus_bonus_related_4e5f6a_idx"
            ),
        ),
    ]
