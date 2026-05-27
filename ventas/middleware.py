# ventas/middleware.py
from django.contrib.auth.models import AnonymousUser
from ventas.models import Clientes
import logging

logger = logging.getLogger('auth.debug')

class ClientesAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
        # ✅ Solo rutas estrictamente públicas (NO incluir /login/)
        self.public_paths = [
            '/recuperar-password/',
            '/reset-password/',
            '/verificar-email/',
            '/reenviar-verificacion/',
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        # Excluir rutas públicas
        if any(request.path.startswith(path) for path in self.public_paths):
            return self.get_response(request)
        
        # Verificar sesión de cliente
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
                request.user = cliente
                
            except Clientes.DoesNotExist:
                for key in ['cliente_id', 'cliente_auth', 'cliente_nombre', 'cliente_email']:
                    request.session.pop(key, None)
                request.cliente = None
                from django.contrib.auth.models import AnonymousUser
                request.user = AnonymousUser()
        else:
            request.cliente = None
        
        response = self.get_response(request)
        return response