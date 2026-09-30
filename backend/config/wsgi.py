"""
WSGI config for Ringoo project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()


def _ensure_vercel_catalog() -> None:
    """Если Postgres не подключена, витрина из 5 товаров собирается в /tmp при старте."""
    if os.environ.get('VERCEL') != '1':
        return
    if os.environ.get('DATABASE_URL', '').strip():
        return
    if os.environ.get('RINGOO_VERCEL_BUILD') == '1':
        return
    from django.core.management import call_command

    from apps.products.models import Product

    call_command('migrate', '--noinput')
    if not Product.objects.filter(slug='xiaomi-15').exists():
        call_command('seed_vercel_showcase')


_ensure_vercel_catalog()
