# usuarios/middleware.py
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
import time

from .models import Usuarios

# ─────────────────────────────────────────────────────────────
# CONSTANTES CENTRALIZADAS
# ─────────────────────────────────────────────────────────────
ROLES_SIN_ACCESO_DASHBOARD = ['CLIENTE']

DASHBOARD_PREFIXES = ('/dashboard/',)

PUBLIC_PATHS = (
    '/pagina/',
    '/static/',
    '/media/',
    '/admin/',
    '/accounts/',
)


class CustomAuthMiddleware:
    """
    Middleware para manejar sesión de usuarios STAFF (Usuarios).
    Compatible con ClientesAuthMiddleware.
    Bloquea acceso al dashboard a usuarios sin sesión o con rol CLIENTE.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # ── Rutas excluidas del middleware ────────────────────
        if path.startswith('/admin/') or path.startswith('/accounts/'):
            return self.get_response(request)

        # ── Si ya hay un cliente autenticado, no interferir ───
        if request.session.get('cliente_auth'):
            # Pero si intenta entrar al dashboard, bloquearlo
            if any(path.startswith(p) for p in DASHBOARD_PREFIXES):
                return redirect('/pagina/')
            return self.get_response(request)

        # ── Resolver usuario STAFF desde sesión ──────────────
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
                # Sesión inválida → limpiar y tratar como anónimo
                request.session.pop('usuario_id', None)
                request.user = AnonymousUser()
                if hasattr(request, 'usuario'):
                    delattr(request, 'usuario')
        else:
            request.user = AnonymousUser()
            if hasattr(request, 'usuario'):
                delattr(request, 'usuario')

        # ── Protección del dashboard ──────────────────────────
        if any(path.startswith(p) for p in DASHBOARD_PREFIXES):
            user = request.user

            # Sin sesión → login con ?next=
            if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
                return redirect(f'/pagina/login/?next={path}')

            # CLIENTE autenticado → home público
            if hasattr(user, 'id_rol') and user.id_rol:
                if user.id_rol.nombre_rol in ROLES_SIN_ACCESO_DASHBOARD:
                    return redirect('/pagina/')

        return self.get_response(request)


class NoCacheMiddleware:
    """
    Previene caché del navegador en páginas autenticadas y en el dashboard.
    Impide ver páginas protegidas con el botón Atrás tras hacer logout.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        is_authenticated = (
            (hasattr(request, 'user') and not request.user.is_anonymous) or
            request.session.get('cliente_auth') or
            request.session.get('usuario_id')
        )

        is_dashboard = any(request.path.startswith(p) for p in DASHBOARD_PREFIXES)

        is_auth_page = request.path in [
            '/usuarios/login/', '/usuarios/logout/',
            '/pagina/login/', '/pagina/logout/',
            '/admin/login/', '/admin/logout/',
        ]

        # Aplicar no-cache en dashboard siempre, y en páginas auth/autenticadas
        if is_dashboard or is_authenticated or is_auth_page:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['Surrogate-Control'] = 'no-store'

        return response


class SessionIdleTimeoutMiddleware:
    """
    Cierra sesión después de 10 minutos de inactividad.
    Redirige siempre al home público, nunca al dashboard.
    """
    IDLE_TIMEOUT = 600  # 10 minutos

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Excluir admin nativo de Django
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        usuario_id = request.session.get('usuario_id')
        cliente_auth = request.session.get('cliente_auth')

        if usuario_id or cliente_auth:
            now = time.time()
            last_activity = request.session.get('last_activity_timestamp')

            if last_activity and (now - last_activity) > self.IDLE_TIMEOUT:
                is_cliente = bool(cliente_auth)
                request.session.flush()

                # Siempre redirige a login público, nunca al dashboard
                login_url = reverse('pagina:login')

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(
                        {'error': 'session_expired', 'redirect': str(login_url)},
                        status=401
                    )
                return redirect(f'{login_url}?timeout=1')

            request.session['last_activity_timestamp'] = now

        return self.get_response(request)