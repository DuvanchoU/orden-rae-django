from django.shortcuts import render, redirect, get_object_or_404
from gestion.models import Pedido, Clientes
from django.db import IntegrityError
from django.utils import timezone

# 1. LEER (READ) + REPORTES (ÍTEM 10: Filtros)
def lista_pedidos(request):
    busqueda = request.GET.get('cliente', '')
    estado = request.GET.get('estado', '')
    
    pedidos = Pedido.objects.all()  # <-- Pedido en singular
    
    if busqueda:
        pedidos = pedidos.filter(cliente__nombre__icontains=busqueda) 
    
    if estado:
        # El campo real es estado_pedido
        pedidos = pedidos.filter(estado_pedido=estado) 
        
    # Ordenamiento por fecha_pedido
    pedidos = pedidos.order_by('-fecha_pedido') 
    
    # Calcular total para la tarjeta (usando el campo real total_pedido)
    total_ingresos = sum(p.total_pedido for p in pedidos) if pedidos else 0

    contexto = {
        'pedidos': pedidos,
        'busqueda': busqueda,
        'total_ingresos': total_ingresos
    }
    return render(request, 'gestion/pedidos_lista.html', contexto)

# 2. CREAR (CREATE) + VALIDACIÓN (ÍTEM 7)
def crear_pedido(request):
    if request.method == 'POST':
        try:
            id_cliente = request.POST.get('cliente')
            total = request.POST.get('total')
            estado = request.POST.get('estado')
            direccion = request.POST.get('direccion')
            
            # Validación manual (Ítem 7)
            if not id_cliente or float(total) <= 0:
                raise ValueError("El cliente es obligatorio y el total debe ser mayor a 0")

            # Guardamos en BD con los nombres de campo REALES de tu modelo
            Pedido.objects.create(
                cliente_id=id_cliente,
                total_pedido=total,          
                estado_pedido=estado,
                direccion_entrega=direccion,       
                usuario_id=1,                # <-- Usuario por defecto (ajústalo)
                fecha_pedido=timezone.now()  # <-- Necesitas importar timezone
            )
            return redirect('lista_pedidos')
            
        except IntegrityError:
            return render(request, 'gestion/crear_pedido.html', {'error': 'Error de integridad en la base de datos.'})
        except Exception as e:
            return render(request, 'gestion/crear_pedido.html', {'error': f'Ocurrió un error: {str(e)}'})

    clientes = Clientes.objects.all()
    return render(request, 'gestion/crear_pedido.html', {'clientes': clientes})

# 3. ELIMINAR (DELETE)
def eliminar_pedido(request, id_pedido):
    try:
        # El campo primary key es id_pedido, no id
        pedido = Pedido.objects.get(id_pedido=id_pedido)
        pedido.delete()
    except Pedido.DoesNotExist:
        pass
    return redirect('lista_pedidos')