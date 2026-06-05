# ventas/context_processors.py
from ventas.models import Carritos, ItemsCarrito, Clientes
from django.db.models import Sum


def carrito_context(request):
    """
    Context processor para el carrito de compras.
    Calcula la cantidad de items en el carrito.
    """
    carrito_cantidad = 0

    try:
        # Si es usuario staff (tiene id_usuario), no tiene carrito
        if hasattr(request.user, 'id_usuario'):
            return {'carrito_cantidad': 0}

        if request.user.is_authenticated:
            # Es cliente autenticado
            cliente = None
            if hasattr(request.user, 'id_cliente'):
                cliente = request.user
            else:
                cliente = Clientes.objects.filter(
                    email=request.user.email,
                    deleted_at__isnull=True
                ).first()

            if cliente:
                carrito = Carritos.objects.filter(
                    cliente=cliente,
                    deleted_at__isnull=True
                ).first()

                if carrito:
                    result = ItemsCarrito.objects.filter(
                        carrito=carrito
                    ).aggregate(total=Sum('cantidad'))
                    carrito_cantidad = result['total'] or 0
        else:
            # Usuario anónimo — usar session_id
            session_id = request.session.session_key
            if session_id:
                carrito = Carritos.objects.filter(
                    session_id=session_id,
                    deleted_at__isnull=True
                ).first()

                if carrito:
                    result = ItemsCarrito.objects.filter(
                        carrito=carrito
                    ).aggregate(total=Sum('cantidad'))
                    carrito_cantidad = result['total'] or 0

    except Exception as e:
        print(f"Error en carrito_context: {e}")

    return {'carrito_cantidad': carrito_cantidad}


def cliente_auth_context(request):
    """
    Context processor para la autenticación del cliente.
    Hace disponible la información del cliente en TODAS las plantillas.
    """
    context = {
        'cliente_auth': False,
        'cliente_id': None,
        'cliente_nombre': '',
        'cliente_email': '',
        'cliente': None,
    }
    
    # Verificar si hay sesión de cliente
    if request.session.get('cliente_auth'):
        cliente_id = request.session.get('cliente_id')
        
        if cliente_id:
            try:
                cliente = Clientes.objects.get(
                    id_cliente=cliente_id,
                    estado='ACTIVO',
                    deleted_at__isnull=True
                )
                
                context.update({
                    'cliente_auth': True,
                    'cliente_id': cliente.id_cliente,
                    'cliente_nombre': f"{cliente.nombre} {cliente.apellido}",
                    'cliente_email': cliente.email,
                    'cliente': cliente,
                })
                
                # Actualizar también request.cliente si existe
                if hasattr(request, 'cliente'):
                    request.cliente = cliente
                    
            except Clientes.DoesNotExist:
                # Limpiar sesión si el cliente no existe
                for key in ['cliente_id', 'cliente_auth', 'cliente_nombre', 'cliente_email']:
                    request.session.pop(key, None)
    
    return context