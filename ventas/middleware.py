# ventas/middleware.py
from django.contrib.auth.models import AnonymousUser
from ventas.models import Clientes
import logging

logger = logging.getLogger('auth.debug')


class ClientesAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        # === Verificar sesión de cliente PRIMERO (antes de cualquier otra cosa) ===
        cliente_id = request.session.get('cliente_id')
        cliente_auth = request.session.get('cliente_auth', False)
        
        if cliente_id and cliente_auth:
            try:
                cliente = Clientes.objects.get(
                    pk=cliente_id,
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                request.cliente = cliente
                request.user = cliente  # Sobreescribe lo que puso AuthenticationMiddleware
                logger.debug(f" [ClientesMW] Cliente autenticado: {cliente.email}")
                
            except Clientes.DoesNotExist:
                logger.warning(f" [ClientesMW] Cliente ID {cliente_id} no encontrado")
                for key in ['cliente_id', 'cliente_auth', 'cliente_nombre', 'cliente_email']:
                    request.session.pop(key, None)
                request.cliente = None
                request.user = AnonymousUser()
        else:
            request.cliente = None
            # Solo poner AnonymousUser si no hay staff autenticado
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                request.user = AnonymousUser()
            # Si hay staff autenticado (id_usuario), no tocar
        
        response = self.get_response(request)
        return response