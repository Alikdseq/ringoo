#!/usr/bin/env python
"""
Скрипт для тестирования Sentry.
Использование: python test_sentry.py
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.conf import settings
import sentry_sdk


def test_sentry():
    """Тестирование Sentry."""
    print("=" * 60)
    print("Тестирование Sentry")
    print("=" * 60)
    
    # Проверка конфигурации
    print("\n1. Проверка конфигурации Sentry...")
    sentry_dsn = os.getenv('SENTRY_DSN', '')
    
    if not sentry_dsn:
        print("   ⚠️  SENTRY_DSN не настроен")
        print("   💡 Для тестирования:")
        print("      1. Зарегистрируйтесь на https://sentry.io")
        print("      2. Создайте проект Django")
        print("      3. Скопируйте DSN")
        print("      4. Добавьте в .env.development: SENTRY_DSN=your-dsn-here")
        print("\n   ℹ️  Sentry отключен (это нормально для development)")
        return True
    
    print(f"   ✅ SENTRY_DSN настроен: {sentry_dsn[:20]}...")
    
    # Проверка что Sentry SDK инициализирован
    print("\n2. Проверка инициализации Sentry SDK...")
    try:
        client = sentry_sdk.Hub.current.client
        if client:
            print("   ✅ Sentry SDK инициализирован")
            print(f"   📊 Environment: {client.options.get('environment', 'unknown')}")
            print(f"   📊 DSN: {client.dsn}")
        else:
            print("   ⚠️  Sentry SDK не инициализирован")
            return False
    except Exception as e:
        print(f"   ⚠️  Ошибка проверки: {e}")
        return False
    
    # Тест отправки сообщения
    print("\n3. Тест отправки сообщения в Sentry...")
    try:
        sentry_sdk.capture_message("Test message from Ringoo - Sentry is working!", level="info")
        print("   ✅ Тестовое сообщение отправлено")
        print("   💡 Проверьте ваш Sentry dashboard для подтверждения")
    except Exception as e:
        print(f"   ❌ Ошибка отправки: {e}")
        return False
    
    # Тест отправки исключения
    print("\n4. Тест отправки исключения в Sentry...")
    try:
        try:
            # Искусственное исключение для теста
            raise ValueError("Test exception for Sentry - this is intentional")
        except ValueError as e:
            sentry_sdk.capture_exception(e)
            print("   ✅ Тестовое исключение отправлено")
            print("   💡 Проверьте ваш Sentry dashboard для подтверждения")
    except Exception as e:
        print(f"   ❌ Ошибка отправки исключения: {e}")
        return False
    
    # Тест фильтрации чувствительных данных
    print("\n5. Тест фильтрации чувствительных данных...")
    try:
        # Попытка отправить событие с чувствительными данными
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("password", "secret123")
            scope.set_extra("api_key", "key12345")
            scope.set_user({"email": "test@example.com", "username": "testuser"})
            sentry_sdk.capture_message("Test with sensitive data filtering")
        print("   ✅ Тест фильтрации выполнен")
        print("   💡 Проверьте в Sentry что чувствительные данные отфильтрованы")
    except Exception as e:
        print(f"   ⚠️  Ошибка теста фильтрации: {e}")
    
    # Проверка интеграций
    print("\n6. Проверка интеграций...")
    integrations = client.options.get('integrations', [])
    integration_names = [type(i).__name__ for i in integrations]
    print(f"   📦 Активные интеграции: {', '.join(integration_names)}")
    
    if 'DjangoIntegration' in integration_names:
        print("   ✅ Django интеграция активна")
    if 'CeleryIntegration' in integration_names:
        print("   ✅ Celery интеграция активна")
    if 'LoggingIntegration' in integration_names:
        print("   ✅ Logging интеграция активна")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование Sentry завершено!")
    print("=" * 60)
    print("\n📝 Следующие шаги:")
    print("   1. Откройте ваш Sentry dashboard")
    print("   2. Проверьте что тестовые сообщения и исключения появились")
    print("   3. Убедитесь что чувствительные данные отфильтрованы")
    return True


if __name__ == '__main__':
    success = test_sentry()
    sys.exit(0 if success else 1)
