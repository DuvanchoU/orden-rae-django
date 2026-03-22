from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from .models import Clientes, Pedido, Ventas, Cotizaciones, DetalleVenta, DetalleCotizacion, Carritos, ItemsCarrito, DetallePedido, MetodosPago
from inventario.models import Producto
from usuarios.models import Usuarios
from django.contrib import messages
from django.utils import timezone
from .forms import ClienteForm, PedidoForm, VentaForm, CotizacionForm

# CLIENTES
class ClienteListView(ListView):
    model = Clientes
    template_name = 'ventas/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) |
                Q(apellido__icontains=busqueda) |
                Q(email__icontains=busqueda) |
                Q(telefono__icontains=busqueda)
            )
        return queryset.order_by('-fecha_registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = ['ACTIVO', 'INACTIVO']
        return context


class ClienteCreateView(CreateView):
    model = Clientes
    template_name = 'ventas/cliente_form.html'
    form_class = ClienteForm
    success_url = reverse_lazy('ventas:cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Cliente'
        return context


class ClienteUpdateView(UpdateView):
    model = Clientes
    template_name = 'ventas/cliente_form.html'
    form_class = ClienteForm
    success_url = reverse_lazy('ventas:cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cliente'
        return context


class ClienteDeleteView(DeleteView):
    model = Clientes
    template_name = 'ventas/cliente_confirm_delete.html'
    success_url = reverse_lazy('ventas:cliente_list')


class ClienteDetailView(DetailView):
    model = Clientes
    template_name = 'ventas/cliente_detail.html'
    context_object_name = 'cliente'

# PEDIDOS
class PedidoListView(ListView):
    model = Pedido
    template_name = 'ventas/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.GET.get('cliente')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        busqueda = self.request.GET.get('busqueda')
        entrega_desde = self.request.GET.get('entrega_desde')
        entrega_hasta = self.request.GET.get('entrega_hasta')

        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if estado:
            queryset = queryset.filter(estado_pedido=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_pedido__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_pedido__lte=fecha_fin)
        if entrega_desde:
            queryset = queryset.filter(fecha_entrega_estimada__gte=entrega_desde)
        if entrega_hasta:
            queryset = queryset.filter(fecha_entrega_estimada__lte=entrega_hasta)
        if busqueda:
            queryset = queryset.filter(
                Q(numero_pedido__icontains=busqueda) |
                Q(cliente__nombre__icontains=busqueda)
            )
        return queryset.order_by('-fecha_pedido')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.all()
        context['estados'] = ['PENDIENTE', 'CONFIRMADO', 'EN PROCESO', 'COMPLETADO', 'CANCELADO']
        return context


class PedidoCreateView(CreateView):
    model = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class = PedidoForm
    success_url = reverse_lazy('ventas:pedido_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Pedido'
        context['clientes'] = Clientes.objects.all()
        return context

    def form_valid(self, form):
        form.instance.usuario_id = 1  # Cambiar por request.user.id cuando tengas auth
        form.instance.fecha_pedido = timezone.now()
        return super().form_valid(form)


class PedidoUpdateView(UpdateView):
    model = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class = PedidoForm
    success_url = reverse_lazy('ventas:pedido_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Pedido'
        context['clientes'] = Clientes.objects.all()
        return context


class PedidoDeleteView(DeleteView):
    model = Pedido
    template_name = 'ventas/pedido_confirm_delete.html'
    success_url = reverse_lazy('ventas:pedido_list')


class PedidoDetailView(DetailView):
    model = Pedido
    template_name = 'ventas/pedido_detail.html'
    context_object_name = 'pedido'

# VENTAS
class VentaListView(ListView):
    model = Ventas
    template_name = 'ventas/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.GET.get('cliente')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')

        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if estado:
            queryset = queryset.filter(estado_venta=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_venta__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_venta__lte=fecha_fin)
        return queryset.order_by('-fecha_venta')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.all()
        context['estados'] = ['PENDIENTE', 'COMPLETADA', 'CANCELADA']
        return context


class VentaCreateView(CreateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm
    success_url = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Venta'
        context['clientes'] = Clientes.objects.all()
        context['pedido'] = Pedido.objects.filter(estado_pedido='COMPLETADO')
        return context


class VentaUpdateView(UpdateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm
    success_url = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Venta'
        context['clientes'] = Clientes.objects.all()
        context['pedido'] = Pedido.objects.filter(estado_pedido='COMPLETADO')
        return context


class VentaDeleteView(DeleteView):
    model = Ventas
    template_name = 'ventas/venta_confirm_delete.html'
    success_url = reverse_lazy('ventas:venta_list')

class VentaDetailView(DetailView):
    model = Ventas
    template_name = 'ventas/venta_detail.html'
    context_object_name = 'venta'

# ventas/views.py
from .forms import VentaForm  # ← Importar

class VentaCreateView(CreateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm  # ← Cambiar fields → form_class
    success_url = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Venta'
        return context


class VentaUpdateView(UpdateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm  # ← Cambiar fields → form_class
    success_url = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Venta'
        return context
        

# COTIZACIONES
class CotizacionListView(ListView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_list.html'
    context_object_name = 'cotizaciones'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente = self.request.GET.get('cliente')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        busqueda = self.request.GET.get('busqueda')

        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_cotizacion__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_cotizacion__lte=fecha_fin)
        if busqueda:
            queryset = queryset.filter(
                Q(numero_cotizacion__icontains=busqueda) |
                Q(cliente__nombre__icontains=busqueda)
            )
        return queryset.order_by('-fecha_cotizacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.all()
        return context


class CotizacionCreateView(CreateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class = CotizacionForm
    success_url = reverse_lazy('ventas:cotizacion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Cotización'
        context['clientes'] = Clientes.objects.all()
        return context


class CotizacionUpdateView(UpdateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class = CotizacionForm
    success_url = reverse_lazy('ventas:cotizacion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cotización'
        context['clientes'] = Clientes.objects.all()
        return context


class CotizacionDeleteView(DeleteView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_confirm_delete.html'
    success_url = reverse_lazy('ventas:cotizacion_list')

class CotizacionDetailView(DetailView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_detail.html'
    context_object_name = 'cotizacion'
    pk_url_kwarg = 'pk'


# Carrito
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from inventario.models import Producto, Inventario
from django.db import models

def get_or_create_carrito(request):
    """Obtiene o crea carrito para usuario autenticado o sesión anónima"""
    if request.user.is_authenticated:
        cliente = Clientes.objects.filter(email=request.user.email).first()
        if not cliente:
            # Crear cliente automático si no existe
            cliente = Clientes.objects.create(
                nombre=request.user.get_full_name() or request.user.username,
                email=request.user.email,
                fecha_registro=timezone.now()
            )
        carrito, created = Carritos.objects.get_or_create(cliente=cliente)
    else:
        # Para usuarios no autenticados → usamos session_id
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
        carrito, created = Carritos.objects.get_or_create(session_id=session_id)
    
    return carrito


@login_required  # o quitar si permites carrito anónimo
def carrito_compra(request):
    carrito = get_or_create_carrito(request)
    items_qs = carrito.itemscarrito_set.select_related('producto')
    
    items = []
    total_carrito = 0
    total_iva = 0
    
    for item in items_qs:
        subtotal = item.precio_unitario * item.cantidad
        iva_item = subtotal * 0.19  # ajusta según tu IVA real
        
        items.append({
            'producto_id': item.producto.id_producto,
            'nombre': item.producto.referencia_producto or item.producto.codigo_producto,
            'sku': item.producto.codigo_producto,
            'precio_base': float(item.precio_unitario),
            'cantidad': item.cantidad,
            'subtotal': float(subtotal),
            'iva': float(iva_item),
            'imagen_url': item.producto.get_imagen_principal().ruta_imagen if item.producto.get_imagen_principal() else '/static/img/placeholder.jpg',
            'stock': item.producto.get_stock_total(),
            'item_id': item.id_item,  # para eliminar/actualizar
        })
        total_carrito += subtotal
        total_iva += iva_item

    context = {
        'carrito_items': items,
        'carrito_cantidad': sum(i.cantidad for i in ItemsCarrito.objects.filter(carrito=carrito)),
        'total_carrito': float(total_carrito),
        'total_iva': float(total_iva),
        'carrito_items_json': items,  # para tu JS si lo necesitas
    }
    
    return render(request, 'pagina/carrito.html', context)


@require_POST
def api_carrito_agregar(request):
    print("=== API AGREGAR CARRITO INICIADA ===")
    print("POST data:", dict(request.POST))
    
    try:
        producto_id = request.POST.get('producto_id')
        if not producto_id:
            raise ValueError("producto_id no recibido")
        
        cantidad_str = request.POST.get('cantidad', '1')
        cantidad = int(cantidad_str)
        
        precio = float(request.POST.get('precio', 0))
        nombre = request.POST.get('nombre', '')
        
        print(f"Buscando producto ID: {producto_id}")
        producto = Producto.objects.get(id_producto=producto_id)
        print(f"Producto encontrado: {producto}")
        
        carrito = get_or_create_carrito(request)
        print(f"Carrito obtenido/creado: ID {carrito.id_carrito}")
        
        # Stock check
        stock_disponible = producto.get_stock_total()
        print(f"Stock disponible: {stock_disponible}")
        if stock_disponible < cantidad:
            return JsonResponse({
                'success': False,
                'error': f'Solo hay {stock_disponible} unidades disponibles'
            }, status=400)
        
        # Crear/actualizar item
        print("Creando/actualizando item...")
        item, created = ItemsCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={
                'precio_unitario': producto.precio_actual,
                'cantidad': cantidad
            }
        )
        if not created:
            item.cantidad += cantidad
            item.save()
        print(f"Item {'creado' if created else 'actualizado'}: {item}")
        
        # Reserva de stock
        print("Reservando stock...")
        inventarios = Inventario.objects.filter(
            producto=producto,
            cantidad_disponible__gt=0,
            deleted_at__isnull=True
        ).order_by('fecha_registro')
        
        cantidad_pendiente = cantidad
        for inv in inventarios:
            if cantidad_pendiente <= 0:
                break
            disponible = inv.cantidad_disponible - (inv.cantidad_reservada or 0)
            reservar = min(cantidad_pendiente, disponible)
            if reservar > 0:
                inv.cantidad_reservada = (inv.cantidad_reservada or 0) + reservar
                inv.save()
                print(f"Reservado {reservar} en inventario {inv.id_inventario}")
                cantidad_pendiente -= reservar
        
        if cantidad_pendiente > 0:
            print("Advertencia: no se pudo reservar todo el stock")
        
        total_items = ItemsCarrito.objects.filter(carrito=carrito).aggregate(total=models.Sum('cantidad'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'cantidad_total': total_items,
            'mensaje': f'{nombre or producto} × {cantidad} añadido'
        })
    
    except Producto.DoesNotExist:
        print("ERROR: Producto no encontrado")
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return JsonResponse({'success': False, 'error': str(ve)}, status=400)
    
    except Exception as e:
        import traceback
        print("ERROR INESPERADO EN AGREGAR CARRITO:")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': 'Error interno al procesar el carrito. Contacta soporte.'
        }, status=500)


@require_POST
def api_carrito_eliminar(request, item_id):
    try:
        item = get_object_or_404(ItemsCarrito, id_item=item_id, carrito__cliente__email=request.user.email)  # seguridad
        producto = item.producto
        cantidad = item.cantidad
        
        # Liberar reserva
        inventarios = Inventario.objects.filter(producto=producto)
        cantidad_pendiente = cantidad
        for inv in inventarios:
            if cantidad_pendiente <= 0:
                break
            liberar = min(cantidad_pendiente, inv.cantidad_reservada or 0)
            if liberar > 0:
                inv.cantidad_reservada = max(0, (inv.cantidad_reservada or 0) - liberar)
                inv.save()
                cantidad_pendiente -= liberar
        
        item.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def api_carrito_actualizar(request, item_id):
    try:
        item = get_object_or_404(ItemsCarrito, id_item=item_id, carrito__cliente__email=request.user.email)
        nueva_cantidad = int(request.POST.get('cantidad', item.cantidad))
        
        if nueva_cantidad < 1:
            return JsonResponse({'success': False, 'error': 'Cantidad inválida'})
        
        diferencia = nueva_cantidad - item.cantidad
        
        # Ajustar reserva
        inventarios = Inventario.objects.filter(producto=item.producto)
        if diferencia > 0:
            # Reservar más
            cantidad_pendiente = diferencia
            for inv in inventarios:
                if cantidad_pendiente <= 0:
                    break
                disponible = inv.cantidad_disponible - (inv.cantidad_reservada or 0)
                reservar = min(cantidad_pendiente, disponible)
                if reservar > 0:
                    inv.cantidad_reservada = (inv.cantidad_reservada or 0) + reservar
                    inv.save()
                    cantidad_pendiente -= reservar
            if cantidad_pendiente > 0:
                return JsonResponse({'success': False, 'error': 'Stock insuficiente para aumentar cantidad'}, status=400)
        elif diferencia < 0:
            # Liberar
            cantidad_pendiente = -diferencia
            for inv in inventarios:
                if cantidad_pendiente <= 0:
                    break
                liberar = min(cantidad_pendiente, inv.cantidad_reservada or 0)
                if liberar > 0:
                    inv.cantidad_reservada = max(0, (inv.cantidad_reservada or 0) - liberar)
                    inv.save()
                    cantidad_pendiente -= liberar
        
        item.cantidad = nueva_cantidad
        item.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)