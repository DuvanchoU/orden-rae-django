# usuarios/utils.py
from django.core.cache import cache
from datetime import datetime, timedelta

def get_login_attempts(request):
    """Obtener número de intentos de login fallidos"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    return cache.get(key, 0)

def increment_login_attempts(request):
    """Incrementar contador de intentos fallidos"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=900)  # 15 minutos
    return attempts

def reset_login_attempts(request):
    """Resetear contador tras login exitoso"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    cache.delete(key)

def is_login_blocked(request):
    """Verificar si la IP está bloqueada temporalmente"""
    ip = get_client_ip(request)
    key = f'login_blocked_{ip}'
    return cache.get(key, False)

def block_login(request, duration=900):
    """Bloquear login por 15 minutos después de 5 intentos fallidos"""
    ip = get_client_ip(request)
    key = f'login_blocked_{ip}'
    cache.set(key, True, timeout=duration)

def get_client_ip(request):
    """Obtener IP real del cliente (funciona detrás de proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip