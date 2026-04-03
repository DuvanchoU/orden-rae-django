# usuarios/backends.py
from django.contrib.auth.backends import BaseBackend
from .models import Usuarios
from django.contrib.auth.hashers import check_password

class UsuariosAuthBackend(BaseBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Si vienen parámetros de cliente, no es un intento de staff
        if kwargs.get('correo') or kwargs.get('contrasena'):
            return None

        if username is None:
            username = kwargs.get('correo_usuario')

        if username is None or password is None:
            return None

        try:
            usuario = Usuarios.objects.select_related('id_rol').get(
                correo_usuario=username,
                estado='ACTIVO',
                deleted_at__isnull=True
            )

            if check_password(password, usuario.contrasena_usuario):
                return usuario
            return None

        except Usuarios.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Usuarios.objects.select_related('id_rol').get(
                id_usuario=user_id
            )
        except Usuarios.DoesNotExist:
            return None