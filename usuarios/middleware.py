# usuarios/middleware.py
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import logout
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
import time

# Importa tu modelo personalizado
from .models import Usuarios


class CustomAuthMiddleware:
    """
    Middleware para manejar la sesión de usuarios personalizados.
    Se ejecuta temprano para asegurar que request.user esté definido.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario_id = request.session.get('usuario_id')
        
        # EXCLUIR Django Admin y URLs de auth nativo
        if request.path.startswith('/admin/') or request.path.startswith('/accounts/'):
            # No aplicar lógica personalizada, dejar que Django maneje auth nativo
            return self.get_response(request)
        
        usuario_id = request.session.get('usuario_id')

        if usuario_id:
            try:
                # Intentar obtener el usuario activo
                usuario = Usuarios.objects.get(id_usuario=usuario_id, estado='ACTIVO')
                request.user = usuario
                # Opcional: Actualizar timestamp de actividad aquí también
                request.session['last_activity_timestamp'] = time.time()
                
            except Usuarios.DoesNotExist:
                # Si no existe o no está activo, limpiar sesión
                request.session.flush()
                request.user = AnonymousUser()
        else:
            # Si no hay usuario en sesión
            request.user = AnonymousUser()
        
        response = self.get_response(request)
        return response


class NoCacheMiddleware:
    """
    CRÍTICO: Previene que el navegador guarde en caché páginas de usuarios autenticados.
    Esto evita que al presionar 'atrás' se muestre contenido de una sesión ya cerrada.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Aplicar solo si el usuario está autenticado (según tu lógica personalizada)
        # O si la ruta es sensible (dashboard, admin, etc.)
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Surrogate-Control'] = 'no-store'
        
        # También aplicar a páginas de login/logout para evitar caché de credenciales
        if request.path in ['/usuarios/login/', '/usuarios/logout/', '/admin/']:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response


class SessionIdleTimeoutMiddleware:
    """
    Cierra la sesión del usuario después de 10 minutos de inactividad.
    """
    IDLE_TIMEOUT = 600  # 10 minutos en segundos
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Excluir rutas de admin y auth nativo para no interferir con su manejo
        if request.path.startswith('/admin/'):
            return self.get_response(request)    

        # Solo aplicar a usuarios autenticados
        if hasattr(request, 'user') and request.user.is_authenticated:
            now = time.time()
            last_activity = request.session.get('last_activity_timestamp')
            
            # Si existe última actividad y superó el timeout → cerrar sesión
            if last_activity and (now - last_activity) > self.IDLE_TIMEOUT:
                logout(request)  # Cierra sesión de forma segura
                request.session.flush()  # Limpia la sesión completamente
                
                # Si es petición AJAX, retornar 401
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(
                        {'error': 'session_expired', 'redirect': str(reverse('usuarios:login'))}, 
                        status=401
                    )
                else:
                    # Guardar URL a la que intentaba acceder para redirigir después del login
                    request.session['next_after_login'] = request.get_full_path()
                    return redirect(f"{reverse('usuarios:login')}?timeout=1")
            
            # Actualizar timestamp de última actividad en cada request
            request.session['last_activity_timestamp'] = now
        
        response = self.get_response(request)
        return response