# ventas/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password as django_check
from ventas.models import Clientes
import hashlib
import hmac
import logging

try:
    import bcrypt
    BCRYPT_DISPONIBLE = True
except ImportError:
    BCRYPT_DISPONIBLE = False

logger = logging.getLogger('auth.debug')


def _verificar_password_cliente(password_plano: str, hash_guardado: str) -> bool:
    """
    Verifica contraseña aceptando 3 formatos:
    - pbkdf2_sha256$...  → hasher moderno de Django
    - $2y$... / $2a$... / $2b$... → bcrypt heredado de Laravel
    - hash SHA-256 plano → legacy (64 caracteres hex)

    Usa hmac.compare_digest para el caso SHA-256 para evitar timing attacks.
    """
    if not hash_guardado:
        return False

    # 1. Hash moderno de Django
    if hash_guardado.startswith('pbkdf2_'):
        return django_check(password_plano, hash_guardado)

    # 2. Bcrypt heredado (Laravel usa $2y$, Python bcrypt prefiere $2b$)
    if hash_guardado.startswith(('$2y$', '$2a$', '$2b$')):
        if not BCRYPT_DISPONIBLE:
            logger.error("bcrypt no está instalado. No se puede verificar hash heredado.")
            return False
        try:
            hash_normalizado = '$2b$' + hash_guardado[4:]
            return bcrypt.checkpw(
                password_plano.encode('utf-8'),
                hash_normalizado.encode('utf-8')
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Error verificando bcrypt: {e}")
            return False

    # 3. SHA-256 legacy (comparación de tiempo constante)
    sha_hash = hashlib.sha256(password_plano.encode('utf-8')).hexdigest()
    return hmac.compare_digest(sha_hash, hash_guardado)


class ClientesAuthBackend(BaseBackend):
    """
    Backend de autenticación para clientes de la tienda web.
    Acepta 3 formatos de hash: pbkdf2 (moderno), bcrypt (Laravel heredado),
    y SHA-256 (legacy).
    """

    def authenticate(self, request, correo=None, contrasena=None, **kwargs):
        if not correo or not contrasena:
            return None

        try:
            cliente = Clientes.objects.get(
                email=correo.lower().strip(),
                deleted_at__isnull=True
            )
            logger.debug(f"Cliente encontrado: {cliente.email}, estado: {cliente.estado}")

            # Verificar estado del cliente
            if cliente.estado != 'ACTIVO':
                logger.warning(f"Cliente inactivo: {correo}")
                return None

            # Verificación multi-formato (pbkdf2 + bcrypt + SHA-256)
            if _verificar_password_cliente(contrasena, cliente.contrasena_cliente):
                logger.debug(f"Contraseña correcta para: {correo}")
                return cliente
            else:
                logger.warning(f"Contraseña incorrecta para: {correo}")
                return None

        except Clientes.DoesNotExist:
            # Un solo bloque except (antes había dos duplicados)
            logger.warning(f"Cliente no existe: {correo}")
            return None

    def get_user(self, user_id):
        try:
            return Clientes.objects.get(pk=user_id)
        except Clientes.DoesNotExist:
            return None