# usuarios/backends.py
from django.contrib.auth.backends import BaseBackend
from .models import Usuarios
import hashlib

class UsuariosAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para el modelo Usuarios.
    Compatible con Django Auth usando tu tabla personalizada.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un usuario buscando por correo_usuario (username)
        """
        if username is None:
            username = kwargs.get('correo_usuario')
        
        if username is None or password is None:
            return None
        
        try:
            # Buscar usuario por correo (que usamos como 'username')
            usuario = Usuarios.objects.get(correo_usuario=username, estado='ACTIVO')
            
            # Verificar contraseña con SHA256
            contrasena_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if usuario.contrasena_usuario == contrasena_hash:
                # ✅ NO asignar propiedades - ya están definidas en el modelo
                # Las propiedades is_authenticated, is_active, etc. 
                # se calculan automáticamente desde el modelo
                
                return usuario  # ✅ Solo retornar el usuario
            else:
                return None
                
        except Usuarios.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """
        Obtiene un usuario por su ID para Django Auth
        """
        try:
            return Usuarios.objects.get(id_usuario=user_id)
        except Usuarios.DoesNotExist:
            return None