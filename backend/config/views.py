"""
Health check endpoint for monitoring.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    """
    Health check endpoint for Docker healthcheck and monitoring.
    Checks database and cache connectivity.
    """
    health_status = {
        'status': 'healthy',
        'database': 'ok',
        'cache': 'ok',
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        health_status['database'] = 'error'
        health_status['database_error'] = str(e)
        health_status['status'] = 'unhealthy'
    
    # Check cache connection
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception('Cache read failed')
    except Exception as e:
        health_status['cache'] = 'error'
        health_status['cache_error'] = str(e)
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
