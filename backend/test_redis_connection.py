#!/usr/bin/env python
"""
Скрипт для тестирования подключения к Redis.
Использование: python test_redis_connection.py
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.cache import cache
from django.conf import settings
from django_redis import get_redis_connection


def test_redis_connection():
    """Тестирование подключения к Redis."""
    print("=" * 60)
    print("Тестирование подключения к Redis")
    print("=" * 60)
    
    try:
        # Проверка настроек
        print("\n1. Проверка настроек Redis...")
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        print(f"   📊 Redis URL: {redis_url}")
        
        celery_broker = settings.CELERY_BROKER_URL
        celery_backend = settings.CELERY_RESULT_BACKEND
        print(f"   🔄 Celery Broker: {celery_broker}")
        print(f"   🔄 Celery Backend: {celery_backend}")
        
        # Проверка кэша
        print("\n2. Проверка кэша (cache)...")
        cache_key = 'test_connection'
        cache_value = 'test_value_12345'
        
        # Запись в кэш
        cache.set(cache_key, cache_value, timeout=10)
        print("   ✅ Запись в кэш успешна")
        
        # Чтение из кэша
        cached_value = cache.get(cache_key)
        if cached_value == cache_value:
            print(f"   ✅ Чтение из кэша успешно: {cached_value}")
        else:
            print(f"   ❌ Ошибка: ожидалось '{cache_value}', получено '{cached_value}'")
            return False
        
        # Удаление тестового ключа
        cache.delete(cache_key)
        print("   ✅ Удаление из кэша успешно")
        
        # Проверка сессий (если используется Redis)
        print("\n3. Проверка session backend...")
        session_engine = settings.SESSION_ENGINE
        print(f"   📦 Session Engine: {session_engine}")
        
        if 'cache' in session_engine or 'redis' in session_engine:
            print("   ✅ Сессии используют Redis")
        else:
            print("   ⚠️  Сессии не используют Redis (это нормально для development)")
        
        # Прямое подключение к Redis через django-redis
        print("\n4. Прямое подключение к Redis...")
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            print("   ✅ Прямое подключение успешно")
            
            # Получить информацию о Redis
            info = redis_conn.info()
            print(f"   📊 Версия Redis: {info.get('redis_version', 'unknown')}")
            print(f"   💾 Используемая память: {info.get('used_memory_human', 'unknown')}")
            print(f"   🔌 Подключенные клиенты: {info.get('connected_clients', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️  Прямое подключение: {e}")
        
        # Проверка Celery подключения (если Celery настроен)
        print("\n5. Проверка Celery конфигурации...")
        try:
            from config.celery import app as celery_app
            broker_url = celery_app.conf.broker_url
            backend_url = celery_app.conf.result_backend
            print(f"   ✅ Celery Broker URL: {broker_url}")
            print(f"   ✅ Celery Backend URL: {backend_url}")
            
            # Попытка подключения к broker
            try:
                with celery_app.connection() as conn:
                    conn.ensure_connection(max_retries=3)
                    print("   ✅ Подключение к Celery broker успешно")
            except Exception as e:
                print(f"   ⚠️  Celery broker: {e}")
        except Exception as e:
            print(f"   ⚠️  Celery не настроен или недоступен: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Все проверки Redis пройдены успешно!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Ошибка подключения к Redis: {type(e).__name__}")
        print(f"   {str(e)}")
        print("=" * 60)
        print("\n💡 Рекомендации:")
        print("   1. Убедитесь что Redis контейнер запущен: docker-compose ps")
        print("   2. Проверьте логи: docker-compose logs redis")
        print("   3. Проверьте переменные окружения: docker-compose exec web env | grep REDIS")
        print("   4. Проверьте что Redis доступен: docker-compose exec redis redis-cli ping")
        return False


if __name__ == '__main__':
    success = test_redis_connection()
    sys.exit(0 if success else 1)
