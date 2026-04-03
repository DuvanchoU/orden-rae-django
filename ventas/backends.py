from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from ventas.models import Clientes
import logging

logger = logging.getLogger('auth.debug')

class ClientesAuthBackend(BaseBackend):
    
    # Autentica clientes usando correo electrónico y contraseña
    def authenticate(self, request, correo=None, contrasena=None, **kwargs):
        if not correo or not contrasena:
            return None
        
        # Intentar encontrar el cliente por correo electrónico
        try:
            cliente = Clientes.objects.get(
                email=correo.lower().strip(),
                deleted_at__isnull=True
            )
            logger.debug(f" Cliente encontrado: {cliente.email}, estado: {cliente.estado}")
            
            # Verificar estado del cliente
            if cliente.estado != 'ACTIVO':
                logger.warning(f" Cliente inactivo: {correo}")
                return None
            
            # Verificar contraseña
            if check_password(contrasena, cliente.contrasena_cliente):
                logger.debug(f" Contraseña correcta para: {correo}")
                return cliente
            else:
                logger.warning(f" Contraseña incorrecta para: {correo}")
                return None
        # Manejar caso donde el cliente no existe
        except Clientes.DoesNotExist:
            logger.warning(f" Cliente no existe: {correo}")
            return None

        except Clientes.DoesNotExist:
            return None