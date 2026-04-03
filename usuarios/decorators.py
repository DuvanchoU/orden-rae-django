from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def login_required_custom(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'is_authenticated') or not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para acceder')
            return redirect('pagina:login') 
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        @login_required_custom
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'id_rol') or not request.user.id_rol:
                messages.error(request, 'Usuario sin rol asignado')
                return redirect('pagina:login') 

            usuario_rol = request.user.id_rol.nombre_rol

            if usuario_rol not in allowed_roles:
                messages.error(request, f'No tienes permisos. Rol requerido: {", ".join(allowed_roles)}')
                return redirect('dashboard:dashboard_home') 

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def check_role(user, allowed_roles):
    if not hasattr(user, 'id_rol') or not user.id_rol:
        return False
    return user.id_rol.nombre_rol in allowed_roles