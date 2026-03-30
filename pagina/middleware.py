from django.contrib.auth.models import AnonymousUser
from ventas.models import Clientes

class ClientesAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.get_response(request)
        
        cliente_id = request.session.get('cliente_id')
        
        if cliente_id:
            try:
                cliente = Clientes.objects.get(
                    pk=cliente_id,
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                request.cliente = cliente
                request.user = cliente
            except Clientes.DoesNotExist:
                if 'cliente_id' in request.session:
                    del request.session['cliente_id']
                request.cliente = None
                request.user = AnonymousUser()
        else:
            request.cliente = None
            if not hasattr(request, 'user'):
                request.user = AnonymousUser()
        
        return self.get_response(request)