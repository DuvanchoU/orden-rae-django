from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from ventas.models import Clientes

class ClientesAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para el modelo Clientes.
    """
    
    def authenticate(self, request, correo=None, contrasena=None, **kwargs):
        if correo is None or contrasena is None:
            return None
        
        try:
            cliente = Clientes.objects.get(
                email__iexact=correo.strip(),
                deleted_at__isnull=True
            )
        except Clientes.DoesNotExist:
            check_password(contrasena, 'pbkdf2_sha256$dummy$dummy$dummy')
            return None
        
        if check_password(contrasena, cliente.contrasena_cliente):
            if cliente.estado == 'ACTIVO':
                return cliente
            return None
        
        return None
    
    def get_user(self, cliente_id):
        try:
            return Clientes.objects.get(pk=cliente_id, deleted_at__isnull=True)
        except Clientes.DoesNotExist:
            return None