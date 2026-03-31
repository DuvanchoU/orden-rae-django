# usuarios/middleware.py
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import logout
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
import time

from .models import Usuarios


class CustomAuthMiddleware:
    """
    Middleware para manejar sesión de usuarios STAFF (Usuarios).
    Compatible con ClientesAuthMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # === EXCLUIR rutas de admin y auth nativo de Django ===
        if request.path.startswith('/admin/') or request.path.startswith('/accounts/'):
            return self.get_response(request)
        
        # === VERIFICAR PRIORIDAD: ¿Es un cliente? ===
        if request.session.get('cliente_auth'):
            # Cliente autenticado - no interferir
            if hasattr(request, 'cliente'):
                request.user = request.cliente
            return self.get_response(request)
        
        # === LÓGICA PARA USUARIOS STAFF ===
        usuario_id = request.session.get('usuario_id')

        if usuario_id:
            try:
                usuario = Usuarios.objects.get(
                    id_usuario=usuario_id, 
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                # Establecer usuario en request
                request.user = usuario
                request.usuario = usuario  # Para compatibilidad
                request.session['last_activity_timestamp'] = time.time()
                
            except Usuarios.DoesNotExist:
                # Usuario no encontrado o inactivo
                if 'usuario_id' in request.session:
                    del request.session['usuario_id']
                request.user = AnonymousUser()
                if hasattr(request, 'usuario'):
                    delattr(request, 'usuario')
        else:
            # No hay usuario en sesión
            request.user = AnonymousUser()
            if hasattr(request, 'usuario'):
                delattr(request, 'usuario')
        
        response = self.get_response(request)
        return response


class NoCacheMiddleware:
    """
    Previene caché del navegador en páginas autenticadas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Determinar si hay algún usuario autenticado
        is_authenticated = (
            (hasattr(request, 'user') and not request.user.is_anonymous) or 
            request.session.get('cliente_auth') or
            request.session.get('usuario_id')
        )
        
        if is_authenticated or request.path in [
            '/usuarios/login/', '/usuarios/logout/', 
            '/pagina/login/', '/pagina/logout/', 
            '/admin/login/', '/admin/logout/'
        ]:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Surrogate-Control'] = 'no-store'
        
        return response


class SessionIdleTimeoutMiddleware:
    """
    Cierra sesión después de 10 minutos de inactividad.
    """
    IDLE_TIMEOUT = 600  # 10 minutos
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Excluir admin nativo de Django
        if request.path.startswith('/admin/'):
            return self.get_response(request)    

        # Verificar si hay sesión activa (staff o cliente)
        usuario_id = request.session.get('usuario_id')
        cliente_auth = request.session.get('cliente_auth')
        
        if usuario_id or cliente_auth:
            now = time.time()
            last_activity = request.session.get('last_activity_timestamp')
            
            if last_activity and (now - last_activity) > self.IDLE_TIMEOUT:
                # Determinar tipo de usuario antes de logout
                is_cliente = cliente_auth is True
                
                # Logout
                logout(request)
                request.session.flush()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    login_url = reverse('pagina:login') if is_cliente else reverse('usuarios:login')
                    return JsonResponse(
                        {'error': 'session_expired', 'redirect': str(login_url)}, 
                        status=401
                    )
                else:
                    # Redirigir al login apropiado
                    login_url = reverse('pagina:login') if is_cliente else reverse('usuarios:login')
                    request.session['next_after_login'] = request.get_full_path()
                    return redirect(f"{login_url}?timeout=1")
            
            # Actualizar timestamp de actividad
            request.session['last_activity_timestamp'] = now
        
        response = self.get_response(request)
        return response