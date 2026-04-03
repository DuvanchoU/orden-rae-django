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
        if request.path.startswith('/admin/') or request.path.startswith('/accounts/'):
            return self.get_response(request)

        # Si ya hay un cliente autenticado, no interferir
        if request.session.get('cliente_auth'):
            return self.get_response(request)

        usuario_id = request.session.get('usuario_id')

        if usuario_id:
            try:
                usuario = Usuarios.objects.select_related('id_rol').get(
                    id_usuario=usuario_id,
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                request.user = usuario
                request.usuario = usuario
                request.session['last_activity_timestamp'] = time.time()

            except Usuarios.DoesNotExist:
                request.session.pop('usuario_id', None)
                # Solo poner AnonymousUser si no hay cliente
                if not request.session.get('cliente_auth'):
                    request.user = AnonymousUser()
                if hasattr(request, 'usuario'):
                    delattr(request, 'usuario')
        else:
            # Solo poner AnonymousUser si no hay cliente autenticado
            if not request.session.get('cliente_auth'):
                request.user = AnonymousUser()
            if hasattr(request, 'usuario'):
                delattr(request, 'usuario')

        return self.get_response(request)


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
                request.session.flush()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    login_url = reverse('pagina:login') if is_cliente else reverse('usuarios:login')
                    return JsonResponse(
                        {'error': 'session_expired', 'redirect': str(login_url)},
                        status=401
                    )
                else:
                    login_url = reverse('pagina:login') if is_cliente else reverse('usuarios:login')
                    return redirect(f"{login_url}?timeout=1")
            
            # Actualizar timestamp de actividad
            request.session['last_activity_timestamp'] = now
        
        response = self.get_response(request)
        return response