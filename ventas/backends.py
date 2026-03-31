from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from ventas.models import Clientes

class ClientesAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para Clientes
    """
    
    def authenticate(self, request, correo=None, contrasena=None, **kwargs):
        if correo is None or contrasena is None:
            return None
        
        try:
            # Buscar por email (case-insensitive)
            cliente = Clientes.objects.get(
                email__iexact=correo.strip(),
                estado='ACTIVO',
                deleted_at__isnull=True
            )
        except Clientes.DoesNotExist:
            # Evitar timing attacks
            check_password(contrasena, 'pbkdf2_sha256$dummy$dummy$dummy')
            return None
        
        # Verificar contraseña
        if check_password(contrasena, cliente.contrasena_cliente):
            return cliente
        
        return None
    
    def get_user(self, cliente_id):
        try:
            return Clientes.objects.get(
                pk=cliente_id,
                deleted_at__isnull=True
            )
        except Clientes.DoesNotExist:
            return None