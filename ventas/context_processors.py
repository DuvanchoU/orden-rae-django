# ventas/context_processors.py
from ventas.models import Carritos, ItemsCarrito, Clientes
from django.db.models import Sum

def carrito_context(request):
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