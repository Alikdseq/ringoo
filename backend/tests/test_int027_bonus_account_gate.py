"""INT-027: при BONUS_ENABLED=False BonusAccount не создаётся."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.bonus.models import BonusAccount


User = get_user_model()


class BonusAccountGateTests(TestCase):
    @override_settings(BONUS_ENABLED=False)
    def test_no_account_when_disabled(self):
        user = User.objects.create_user(
            phone="79001110001",
            email="nobonus@example.com",
            password="pass12345",
        )
        self.assertFalse(BonusAccount.objects.filter(user=user).exists())

    @override_settings(BONUS_ENABLED=True)
    def test_account_when_enabled(self):
        user = User.objects.create_user(
            phone="79001110002",
            email="yesbonus@example.com",
            password="pass12345",
        )
        self.assertTrue(BonusAccount.objects.filter(user=user).exists())
