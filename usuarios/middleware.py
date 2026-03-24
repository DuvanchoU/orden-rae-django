# usuarios/middleware.py
from django.contrib.auth.models import AnonymousUser
from .models import Usuarios

class CustomAuthMiddleware:
    """
    Middleware para manejar la sesión de usuarios personalizados
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario_id = request.session.get('usuario_id')
        
        if usuario_id:
            try:
                # Intentar obtener el usuario activo
                usuario = Usuarios.objects.get(id_usuario=usuario_id, estado='ACTIVO')
                request.user = usuario
                # ✅ NO modificar is_authenticated - Django lo maneja automáticamente
                
            except Usuarios.DoesNotExist:
                # Si no existe o no está activo, limpiar sesión
                request.session.flush()
                request.user = AnonymousUser()
        else:
            # Si no hay usuario en sesión
            request.user = AnonymousUser()
        
        response = self.get_response(request)
        return response