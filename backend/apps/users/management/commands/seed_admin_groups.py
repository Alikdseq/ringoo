"""
Создаёт группы Django для RBAC Admin API.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.admin_api.permissions import ALL_ADMIN_GROUPS


class Command(BaseCommand):
    help = "Создать группы ringoo_* для разграничения Admin API."

    def handle(self, *args, **options):
        for name in ALL_ADMIN_GROUPS:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group: {name}"))
            else:
                self.stdout.write(f"Exists: {name}")
