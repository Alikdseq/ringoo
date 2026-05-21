"""Утилиты приложения stores."""

from django.utils.text import slugify


def generate_unique_manager_slug(name: str, *, exclude_pk=None) -> str:
    """Уникальный slug менеджера из ФИО."""
    from .models import Manager

    base = slugify(name, allow_unicode=True) or "manager"
    slug = base
    n = 2
    qs = Manager.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug
