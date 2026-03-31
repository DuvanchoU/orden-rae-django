# ventas/middleware.py
from django.contrib.auth.models import AnonymousUser
from ventas.models import Clientes
import logging

logger = logging.getLogger('auth.debug')


class ClientesAuthMiddleware:
    """
    Middleware para autenticación de CLIENTES (tabla Clientes).
    Se ejecuta después de AuthenticationMiddleware de Django.
    
    Establece request.user = Cliente si hay sesión activa de cliente.
    NO interfiere con usuarios staff (Usuarios).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # === LOG: Verificar estado inicial ===
        logger.debug(f"🔍 [ClientesMW] Path: {request.path}")
        logger.debug(f"🔍 [ClientesMW] Session keys: {list(request.session.keys())}")
        logger.debug(f"🔍 [ClientesMW] cliente_id: {request.session.get('cliente_id')}")
        logger.debug(f"🔍 [ClientesMW] cliente_auth: {request.session.get('cliente_auth')}")
        
        # === Si ya hay un usuario staff autenticado, NO TOCAR ===
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'id_usuario'):
                logger.debug(f"✅ [ClientesMW] Usuario staff detectado, saltando")
                return self.get_response(request)
        
        # === Verificar sesión de cliente ===
        cliente_id = request.session.get('cliente_id')
        cliente_auth = request.session.get('cliente_auth', False)
        
        if cliente_id and cliente_auth:
            try:
                cliente = Clientes.objects.get(
                    pk=cliente_id,
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                # Establecer cliente en request
                request.cliente = cliente
                request.user = cliente  # ← CRÍTICO: Para @login_required
                logger.debug(f"✅ [ClientesMW] Cliente autenticado: {cliente.email}")
                
            except Clientes.DoesNotExist:
                # Cliente no encontrado o inactivo: limpiar sesión
                logger.warning(f"❌ [ClientesMW] Cliente ID {cliente_id} no encontrado")
                keys_to_delete = ['cliente_id', 'cliente_auth', 'cliente_nombre', 'cliente_email']
                for key in keys_to_delete:
                    if key in request.session:
                        del request.session[key]
                request.cliente = None
                request.user = AnonymousUser()
        else:
            # No hay sesión de cliente activa
            request.cliente = None
            if not hasattr(request, 'user') or request.user.is_anonymous:
                request.user = AnonymousUser()
            logger.debug(f"⚠️ [ClientesMW] No hay sesión de cliente activa")
        
        logger.debug(f"🔍 [ClientesMW] request.user final: {request.user} (anónimo: {request.user.is_anonymous})")
        
        response = self.get_response(request)
        return response