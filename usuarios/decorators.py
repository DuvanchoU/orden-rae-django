from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# Roles que NUNCA pueden acceder al dashboard
ROLES_SIN_ACCESO_DASHBOARD = ['CLIENTE']


def login_required_custom(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # ── 1. Sin sesión → login
        if not hasattr(request.user, 'is_authenticated') or not request.user.is_authenticated:
            return redirect('pagina:login')

        # ── 2. Es CLIENTE → página pública, nunca dashboard
        if hasattr(request.user, 'id_rol') and request.user.id_rol:
            if request.user.id_rol.nombre_rol in ROLES_SIN_ACCESO_DASHBOARD:
                messages.error(request, 'No tienes acceso al panel de administración.')
                return redirect('pagina:home')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # ── 1. Sin sesión → login
            if not hasattr(request.user, 'is_authenticated') or not request.user.is_authenticated:
                return redirect('pagina:login')

            # ── 2. Sin rol asignado → login
            if not hasattr(request.user, 'id_rol') or not request.user.id_rol:
                messages.error(request, 'Tu cuenta no tiene un rol asignado.')
                return redirect('pagina:login')

            usuario_rol = request.user.id_rol.nombre_rol

            # ── 3. Es CLIENTE → siempre a la página pública
            if usuario_rol in ROLES_SIN_ACCESO_DASHBOARD:
                messages.error(request, 'No tienes acceso al panel de administración.')
                return redirect('pagina:home')

            # ── 4. Rol no permitido para esta vista → home del dashboard
            if usuario_rol not in allowed_roles:
                messages.error(request, f'No tienes permisos para esta sección.')
                return redirect('dashboard:dashboard_home')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def check_role(user, allowed_roles):
    if not hasattr(user, 'id_rol') or not user.id_rol:
        return False
    return user.id_rol.nombre_rol in allowed_roles