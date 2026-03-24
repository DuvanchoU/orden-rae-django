# ventas/context_processors.py
from ventas.models import Carritos, ItemsCarrito, Clientes
from django.db.models import Sum

def carrito_context(request):
    """Agrega la cantidad del carrito a todos los templates"""
    carrito_cantidad = 0
    
    try:
        if request.user.is_authenticated:
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
            session_id = request.session.session_key
            if not session_id:
                request.session.create()
                session_id = request.session.session_key
                request.session.save()
            
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
        print(f" Error en carrito_context: {e}")
    
    return {
        'carrito_cantidad': carrito_cantidad
    }