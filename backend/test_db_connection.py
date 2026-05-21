#!/usr/bin/env python
"""
Скрипт для тестирования подключения к PostgreSQL.
Использование: python test_db_connection.py
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection
from django.conf import settings


def test_connection():
    """Тестирование подключения к базе данных."""
    print("=" * 60)
    print("Тестирование подключения к PostgreSQL")
    print("=" * 60)
    
    try:
        # Проверка подключения
        print("\n1. Проверка подключения к БД...")
        connection.ensure_connection()
        print("   ✅ Подключение успешно!")
        
        # Проверка настроек
        print("\n2. Проверка настроек подключения...")
        db = settings.DATABASES['default']
        print(f"   📊 База данных: {db['NAME']}")
        print(f"   🖥️  Хост: {db['HOST']}")
        print(f"   👤 Пользователь: {db['USER']}")
        print(f"   🔌 Порт: {db['PORT']}")
        
        # Выполнение тестового запроса
        print("\n3. Выполнение тестового SQL запроса...")
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ Версия PostgreSQL: {version.split(',')[0]}")
        
        # Проверка списка баз данных
        print("\n4. Проверка доступных баз данных...")
        cursor.execute("""
            SELECT datname 
            FROM pg_database 
            WHERE datistemplate = false 
            ORDER BY datname;
        """)
        databases = [row[0] for row in cursor.fetchall()]
        print(f"   📦 Найдено баз данных: {len(databases)}")
        for db_name in databases:
            marker = "⭐" if db_name == db['NAME'] else "  "
            print(f"   {marker} {db_name}")
        
        # Проверка текущей базы данных
        print("\n5. Проверка текущей базы данных...")
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        print(f"   ✅ Текущая БД: {current_db}")
        
        # Проверка таблиц (до миграций их не должно быть)
        print("\n6. Проверка таблиц в базе данных...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        if tables:
            print(f"   📋 Найдено таблиц: {len(tables)}")
            for table in tables[:10]:  # Показать первые 10
                print(f"      - {table}")
            if len(tables) > 10:
                print(f"      ... и еще {len(tables) - 10} таблиц")
        else:
            print("   ℹ️  Таблиц пока нет (миграции еще не применены)")
        
        print("\n" + "=" * 60)
        print("✅ Все проверки пройдены успешно!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Ошибка подключения: {type(e).__name__}")
        print(f"   {str(e)}")
        print("=" * 60)
        print("\n💡 Рекомендации:")
        print("   1. Убедитесь что PostgreSQL контейнер запущен: docker-compose ps")
        print("   2. Проверьте логи: docker-compose logs db")
        print("   3. Проверьте переменные окружения: docker-compose exec web env | grep DB_")
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
