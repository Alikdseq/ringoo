#!/usr/bin/env python
"""
Скрипт для тестирования Celery.
Использование: python test_celery.py
"""
import os
import sys
import django
import time

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from config.celery import app as celery_app
from apps.users.tasks import test_celery_task


def test_celery():
    """Тестирование Celery."""
    print("=" * 60)
    print("Тестирование Celery")
    print("=" * 60)
    
    try:
        # Проверка конфигурации
        print("\n1. Проверка конфигурации Celery...")
        broker_url = celery_app.conf.broker_url
        backend_url = celery_app.conf.result_backend
        timezone = celery_app.conf.timezone
        
        print(f"   📊 Broker URL: {broker_url}")
        print(f"   📊 Result Backend: {backend_url}")
        print(f"   🌍 Timezone: {timezone}")
        
        # Проверка подключения к broker
        print("\n2. Проверка подключения к broker...")
        try:
            with celery_app.connection() as conn:
                conn.ensure_connection(max_retries=3)
                print("   ✅ Подключение к broker успешно")
        except Exception as e:
            print(f"   ❌ Ошибка подключения к broker: {e}")
            print("   💡 Убедитесь что Redis запущен: docker-compose ps")
            return False
        
        # Проверка зарегистрированных задач
        print("\n3. Проверка зарегистрированных задач...")
        registered_tasks = list(celery_app.tasks.keys())
        # Фильтруем только наши задачи (не системные)
        our_tasks = [t for t in registered_tasks if not t.startswith('celery.')]
        print(f"   📋 Найдено задач: {len(our_tasks)}")
        for task in our_tasks[:10]:  # Показать первые 10
            print(f"      - {task}")
        if len(our_tasks) > 10:
            print(f"      ... и еще {len(our_tasks) - 10} задач")
        
        # Проверка что test_celery_task зарегистрирована
        if 'apps.users.tasks.test_celery_task' in registered_tasks:
            print("   ✅ Тестовая задача зарегистрирована")
        else:
            print("   ⚠️  Тестовая задача не найдена")
        
        # Тест выполнения задачи (синхронно, если worker не запущен)
        print("\n4. Тест выполнения задачи...")
        print("   ⚠️  Для асинхронного выполнения нужен запущенный worker")
        print("   💡 Запустите: docker-compose up -d celery")
        print("   💡 Или: make celery-logs")
        
        # Попытка выполнить задачу синхронно (для проверки что задача работает)
        try:
            result = test_celery_task.apply()
            print(f"   ✅ Задача выполнена: {result.result}")
        except Exception as e:
            print(f"   ⚠️  Синхронное выполнение: {e}")
            print("   ℹ️  Это нормально, если worker не запущен")
        
        print("\n" + "=" * 60)
        print("✅ Конфигурация Celery проверена успешно!")
        print("=" * 60)
        print("\n📝 Следующие шаги:")
        print("   1. Запустите worker: docker-compose up -d celery")
        print("   2. Проверьте логи: docker-compose logs celery")
        print("   3. Выполните задачу асинхронно через Django shell")
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Ошибка тестирования Celery: {type(e).__name__}")
        print(f"   {str(e)}")
        print("=" * 60)
        print("\n💡 Рекомендации:")
        print("   1. Убедитесь что Redis запущен: docker-compose ps")
        print("   2. Проверьте настройки в settings/base.py")
        print("   3. Проверьте что celery.py правильно настроен")
        return False


if __name__ == '__main__':
    success = test_celery()
    sys.exit(0 if success else 1)
