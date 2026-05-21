# Generated manually for CustomUser, UserProfile, DeliveryAddress

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomUser",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, verbose_name="superuser status")),
                ("username", models.CharField(blank=True, max_length=150, null=True, verbose_name="Username (не используется)")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("is_staff", models.BooleanField(default=False, verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, verbose_name="active")),
                ("date_joined", models.DateTimeField(blank=True, default=timezone.now, verbose_name="date joined")),
                ("phone", models.CharField(db_index=True, max_length=20, unique=True, verbose_name="Телефон")),
                ("email", models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name="Email")),
                ("is_phone_verified", models.BooleanField(default=False, verbose_name="Телефон подтверждён")),
                ("is_email_verified", models.BooleanField(default=False, verbose_name="Email подтверждён")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "Пользователь",
                "verbose_name_plural": "Пользователи",
                "db_table": "users_user",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="profile",
                        serialize=False,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, null=True, verbose_name="Имя")),
                ("last_name", models.CharField(blank=True, max_length=150, null=True, verbose_name="Фамилия")),
                ("middle_name", models.CharField(blank=True, max_length=150, null=True, verbose_name="Отчество")),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/%Y/%m/", verbose_name="Аватар")),
                ("birth_date", models.DateField(blank=True, null=True, verbose_name="Дата рождения")),
                (
                    "gender",
                    models.CharField(
                        blank=True,
                        choices=[("M", "Мужской"), ("F", "Женский"), ("O", "Другое")],
                        max_length=1,
                        null=True,
                        verbose_name="Пол",
                    ),
                ),
            ],
            options={
                "verbose_name": "Профиль пользователя",
                "verbose_name_plural": "Профили пользователей",
                "db_table": "users_profile",
            },
        ),
        migrations.CreateModel(
            name="DeliveryAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(help_text='Например: "Дом", "Работа"', max_length=100, verbose_name="Название")),
                ("city", models.CharField(max_length=255, verbose_name="Город")),
                ("street", models.CharField(max_length=255, verbose_name="Улица")),
                ("house", models.CharField(max_length=50, verbose_name="Дом")),
                ("apartment", models.CharField(blank=True, max_length=50, null=True, verbose_name="Квартира")),
                ("postal_code", models.CharField(blank=True, max_length=20, null=True, verbose_name="Индекс")),
                ("is_default", models.BooleanField(default=False, verbose_name="Адрес по умолчанию")),
                (
                    "latitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Широта"),
                ),
                (
                    "longitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name="Долгота"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery_addresses",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Адрес доставки",
                "verbose_name_plural": "Адреса доставки",
                "db_table": "users_delivery_address",
                "ordering": ["-is_default", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="deliveryaddress",
            index=models.Index(fields=["user"], name="users_deladdr_user_idx"),
        ),
        migrations.AddIndex(
            model_name="deliveryaddress",
            index=models.Index(fields=["user", "is_default"], name="users_deladdr_user_default_idx"),
        ),
    ]
