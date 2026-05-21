"""
User-related models: CustomUser, UserProfile, DeliveryAddress.
"""

import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from .services import normalize_phone


class CustomUserManager(UserManager):
    """Менеджер для CustomUser с phone в качестве USERNAME_FIELD (createsuperuser)."""

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        email = extra_fields.pop("email", None)
        if not phone:
            raise ValueError("Нужно указать phone.")
        user = self.model(phone=phone, email=email, username=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(phone, password=password, email=email, **extra_fields)


class CustomUser(AbstractUser):
    """
    Пользователь с телефоном в качестве основного идентификатора.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    phone = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Телефон",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        unique=True,
        verbose_name="Email",
    )
    is_phone_verified = models.BooleanField(
        default=False,
        verbose_name="Телефон подтверждён",
    )
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="Email подтверждён",
    )
    last_login_ip = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        verbose_name="IP последнего успешного входа",
        help_text="Для уведомления о входе с нового адреса (если указан email).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )
    privacy_policy_accepted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Согласие с политикой конфиденциальности (дата)",
    )
    marketing_opt_in = models.BooleanField(
        default=False,
        verbose_name="Согласие на маркетинговые уведомления",
    )
    marketing_opt_in_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата согласия на маркетинг",
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["email"]

    objects = CustomUserManager()

    # AbstractUser имеет поле username; делаем его необязательным при входе по phone
    username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Username (не используется)",
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.phone or str(self.id)

    def save(self, *args, **kwargs):
        # Единый формат в БД (11 цифр, 7…), как при регистрации — иначе вход по API даёт 401
        if self.phone:
            n = normalize_phone(self.phone)
            if n:
                self.phone = n
        # Синхронизация username для совместимости с кодом, ожидающим username
        if self.phone and not self.username:
            self.username = self.phone
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """
    Расширенный профиль пользователя (ФИО, аватар, дата рождения, пол).
    """

    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
        verbose_name="Пользователь",
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Имя",
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Фамилия",
    )
    middle_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Отчество",
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Аватар",
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Дата рождения",
    )
    GENDER_CHOICES = [
        ("M", "Мужской"),
        ("F", "Женский"),
        ("O", "Другое"),
    ]
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name="Пол",
    )

    class Meta:
        db_table = "users_profile"
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self) -> str:
        name = " ".join(
            filter(
                None,
                [self.last_name, self.first_name, self.middle_name],
            )
        )
        return name or str(self.user_id)


class DeliveryAddress(models.Model):
    """
    Адрес доставки пользователя.
    """

    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="delivery_addresses",
        verbose_name="Пользователь",
    )
    title = models.CharField(
        max_length=100,
        verbose_name="Название",
        help_text='Например: "Дом", "Работа"',
    )
    city = models.CharField(
        max_length=255,
        verbose_name="Город",
    )
    street = models.CharField(
        max_length=255,
        verbose_name="Улица",
    )
    house = models.CharField(
        max_length=50,
        verbose_name="Дом",
    )
    apartment = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Квартира",
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Индекс",
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Адрес по умолчанию",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Широта",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name="Долгота",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    class Meta:
        db_table = "users_delivery_address"
        verbose_name = "Адрес доставки"
        verbose_name_plural = "Адреса доставки"
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user", "is_default"]),
        ]

    def __str__(self) -> str:
        return f"{self.title}: {self.city}, {self.street}, {self.house}"


class ConsentRecord(models.Model):
    """Фиксация согласий на обработку ПДн (152-ФЗ)."""

    TYPE_PRIVACY = "privacy"
    TYPE_MARKETING = "marketing"
    TYPE_ORDER_PDN = "order_pdn"
    TYPE_OFFER = "offer"
    TYPE_CRM_LEAD = "crm_lead"
    TYPE_ANALYTICS = "analytics_cookies"
    TYPE_NEWSLETTER = "newsletter"
    TYPE_CHOICES = [
        (TYPE_PRIVACY, "Политика конфиденциальности / согласие на ПДн"),
        (TYPE_MARKETING, "Маркетинг"),
        (TYPE_ORDER_PDN, "ПДн при оформлении заказа"),
        (TYPE_OFFER, "Публичная оферта"),
        (TYPE_CRM_LEAD, "CRM-заявка"),
        (TYPE_ANALYTICS, "Cookie аналитики (Яндекс.Метрика)"),
        (TYPE_NEWSLETTER, "Подписка на рассылку"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consent_records",
        verbose_name="Пользователь",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consent_records",
        verbose_name="Заказ",
    )
    consent_type = models.CharField(max_length=32, choices=TYPE_CHOICES, db_index=True)
    accepted_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата согласия")
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name="IP",
    )
    policy_version = models.CharField(max_length=64, verbose_name="Версия политики")
    user_agent = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        db_table = "users_consent_record"
        verbose_name = "Запись согласия"
        verbose_name_plural = "Записи согласий"
        ordering = ["-accepted_at"]
        indexes = [
            models.Index(fields=["user", "consent_type"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self) -> str:
        return f"{self.consent_type} @ {self.accepted_at}"
