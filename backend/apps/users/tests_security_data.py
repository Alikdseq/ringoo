"""
Маскирование в логах и команда очистки неактивных пользователей (§3 аудита).
"""

import logging
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.users.models import CustomUser
from config.logging_filters import RedactPIIFilter, redact_log_message


class TestRedactLogMessage(SimpleTestCase):
    def test_masks_email(self):
        s = redact_log_message("write to user@example.com now")
        self.assertNotIn("user@example.com", s)

    def test_filter_mutates_record(self):
        log = logging.getLogger("test_redact")
        filt = RedactPIIFilter()
        record = logging.LogRecord(
            name="t",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="phone +79991234567",
            args=(),
            exc_info=None,
        )
        self.assertTrue(filt.filter(record))
        self.assertNotIn("79991234567", record.getMessage())


@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    },
)
class TestCleanupDeactivatedUsersCommand(TransactionTestCase):
    def test_dry_run_does_not_delete(self):
        u = CustomUser.objects.create_user("79995554433", password="secretpass12")
        u.is_active = False
        u.save(update_fields=["is_active"])
        CustomUser.objects.filter(pk=u.pk).update(
            updated_at=timezone.now() - timedelta(days=400)
        )
        out = StringIO()
        call_command("cleanup_deactivated_users", "--min-days", "300", stdout=out)
        self.assertTrue(CustomUser.objects.filter(pk=u.pk).exists())
        self.assertIn("Dry run", out.getvalue())

    def test_execute_removes_stale_inactive(self):
        u = CustomUser.objects.create_user("79995554444", password="secretpass12")
        u.is_active = False
        u.save(update_fields=["is_active"])
        CustomUser.objects.filter(pk=u.pk).update(
            updated_at=timezone.now() - timedelta(days=400)
        )
        out = StringIO()
        call_command(
            "cleanup_deactivated_users",
            "--min-days",
            "300",
            "--execute",
            stdout=out,
        )
        self.assertFalse(CustomUser.objects.filter(pk=u.pk).exists())

    def test_never_touches_staff(self):
        u = CustomUser.objects.create_user(
            "79995554455", password="secretpass12", is_staff=True
        )
        u.is_active = False
        u.save(update_fields=["is_active"])
        CustomUser.objects.filter(pk=u.pk).update(
            updated_at=timezone.now() - timedelta(days=400)
        )
        call_command(
            "cleanup_deactivated_users",
            "--min-days",
            "300",
            "--execute",
            stdout=StringIO(),
        )
        self.assertTrue(CustomUser.objects.filter(pk=u.pk).exists())


class TestAuditLogOnOrderExport(TestCase):
    """Проверка, что экспорт заказов создаёт запись аудита (без полного AdminSite)."""

    def test_log_admin_action_called_from_export_pattern(self):
        from apps.audit.models import AuditLog
        from apps.audit.services import log_admin_action
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff = User.objects.create_user(
            phone="79994443322", password="pw", is_staff=True
        )
        req = RequestFactory().get("/")
        req.user = staff
        before = AuditLog.objects.count()
        log_admin_action(
            req,
            action="order_export_csv",
            model_name="orders.Order",
            object_id="",
            object_repr="export 3 orders",
            changes={"count": 3},
        )
        self.assertEqual(AuditLog.objects.count(), before + 1)
