from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count, F
from django.contrib import messages
from .models import Clientes, Pedido, Ventas, Cotizaciones, DetalleVenta, DetalleCotizacion, Carritos, ItemsCarrito, DetallePedido, MetodosPago
from ventas.models import Clientes, Carritos, ItemsCarrito, Pedido, Ventas, Cotizaciones
from inventario.models import Producto
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .forms import ClienteForm, PedidoForm, VentaForm, CotizacionForm
from django.http import JsonResponse
import json
from django.contrib.auth import login

# CLIENTES
class ClienteListView(ListView):
    model = Clientes
    template_name = 'ventas/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 10

    def get_queryset(self):
        queryset = Clientes.objects.filter(deleted_at__isnull=True)

        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda) |
                Q(apellido__icontains=busqueda) |
                Q(email__icontains=busqueda) |
                Q(telefono__icontains=busqueda) |
                Q(direccion__icontains=busqueda)
            )

        return queryset.order_by('-nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = ['ACTIVO', 'INACTIVO']
        context['titulo'] = 'Clientes'

        # Estadísticas rápidas
        context['total_clientes'] = Clientes.objects.filter(
            deleted_at__isnull=True
        ).count()
        context['clientes_activos'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        ).count()

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

    def form_valid(self, form):
        try:
            cliente = form.save(commit=False)
            cliente.fecha_registro = timezone.now()
            cliente.created_at = timezone.now()
            cliente.updated_at = timezone.now()
            
            if not cliente.estado:
                cliente.estado = 'ACTIVO'
            
            cliente.save()
            
            messages.success(
                self.request, 
                f'Cliente "{cliente.get_nombre_completo()}" registrado exitosamente.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al registrar: {str(e)}')
            return self.form_invalid(form)

class ClienteUpdateView(UpdateView):
    model = Clientes
    template_name = 'ventas/cliente_form.html'
    form_class = ClienteForm
    success_url = reverse_lazy('ventas:cliente_list')

    def get_queryset(self):
        return Clientes.objects.filter(deleted_at__isnull=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cliente'

        # Mostrar alertas si el cliente tiene pedidos
        cliente = self.get_object()
        if cliente.tiene_pedidos_asociados():
            messages.info(
                self.request,
                f"Este cliente tiene {cliente.get_cantidad_pedidos()} pedidos asociados"
            )

        return context

    def form_valid(self, form):
        try:
            cliente = form.save(commit=False)
            cliente.updated_at = timezone.now()
            cliente.save()
            
            messages.success(
                self.request, 
                f'Cliente "{cliente.get_nombre_completo()}" actualizado correctamente.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return self.form_invalid(form)


class ClienteDeleteView(View):
    """Soft delete con validaciones"""
    
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(
                Clientes, 
                pk=pk, 
                deleted_at__isnull=True
            )
            
            if not cliente.puede_eliminarse():
                messages.error(
                    request,
                    f"No se puede eliminar. El cliente tiene pedidos activos o pendientes."
                )
                return redirect('ventas:cliente_list')
            
            cliente.delete()  # Soft delete
            messages.success(
                request, 
                f'Cliente "{cliente.get_nombre_completo()}" eliminado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('ventas:cliente_list')


class ClienteDetailView(DetailView):
    model = Clientes
    template_name = 'ventas/cliente_detail.html'
    context_object_name = 'cliente'

    def get_queryset(self):
        return Clientes.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cliente = self.get_object()
        
        # Total pedidos
        context['total_pedidos'] = Pedido.objects.filter(
            cliente=cliente,
            deleted_at__isnull=True
        ).count()
        
        # Total gastado (solo pedidos completados)
        total = Pedido.objects.filter(
            cliente=cliente,
            deleted_at__isnull=True,
            estado_pedido='COMPLETADO'
        ).aggregate(total=Sum('total_pedido'))['total'] or 0
        context['total_gastado'] = float(total)
        
        # Último pedido
        ultimo = Pedido.objects.filter(
            cliente=cliente,
            deleted_at__isnull=True
        ).order_by('-fecha_pedido').first()
        context['ultimo_pedido'] = ultimo.fecha_pedido.strftime('%d/%m/%y') if ultimo else None
        
        # Últimos 5 pedidos
        context['ultimos_pedidos'] = Pedido.objects.filter(
            cliente=cliente,
            deleted_at__isnull=True
        ).order_by('-fecha_pedido')[:5]
        
        return context


class ClienteActivarView(View):
    """Restaurar cliente eliminado"""
    
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(Clientes, pk=pk)
            cliente.restore()
            messages.success(
                request, 
                f'Cliente "{cliente.get_nombre_completo()}" activado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al activar: {str(e)}')
            return redirect('ventas:cliente_list')


class ClienteDesactivarView(View):
    """Desactivar cliente con validaciones"""
    
    def post(self, request, pk):
        try:
            cliente = get_object_or_404(
                Clientes, 
                pk=pk, 
                deleted_at__isnull=True
            )
            
            cliente.desactivar()
            messages.success(
                request, 
                f'Cliente "{cliente.get_nombre_completo()}" desactivado correctamente.'
            )
            return redirect('ventas:cliente_list')
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:cliente_list')
        except Exception as e:
            messages.error(request, f'Error al desactivar: {str(e)}')
            return redirect('ventas:cliente_list')

# ============================================================================
# PEDIDOS 
# ============================================================================
class PedidoListView(ListView):
    model = Pedido
    template_name = 'ventas/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 10

    def get_queryset(self):
        queryset = Pedido.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario', 'asesor')

        cliente = self.request.GET.get('cliente')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        entrega_desde = self.request.GET.get('entrega_desde')
        entrega_hasta = self.request.GET.get('entrega_hasta')
        busqueda = self.request.GET.get('busqueda')

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
                Q(cliente__nombre__icontains=busqueda) |
                Q(cliente__apellido__icontains=busqueda)
            )

        return queryset.order_by('-fecha_pedido', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        context['estados'] = ['PENDIENTE', 'CONFIRMADO', 'EN PROCESO', 'COMPLETADO', 'CANCELADO']
        context['titulo'] = 'Pedidos'

        # Estadísticas
        context['total_pedidos'] = Pedido.objects.filter(
            deleted_at__isnull=True
        ).count()
        context['pedidos_pendientes'] = Pedido.objects.filter(
            estado_pedido='PENDIENTE',
            deleted_at__isnull=True
        ).count()

        return context


class PedidoCreateView(CreateView):
    model = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class = PedidoForm
    success_url = reverse_lazy('ventas:pedido_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Pedido'
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        return context

    def form_valid(self, form):
        try:
            # Validar que el cliente esté activo
            cliente = form.cleaned_data['cliente']
            if cliente.estado != 'ACTIVO':
                messages.error(
                    self.request,
                    "El cliente seleccionado está inactivo. Active el cliente primero."
                )
                return self.form_invalid(form)
            
            # Crear pedido
            pedido = form.save(commit=False)
            pedido.usuario_id = self.request.user.id if hasattr(self.request, 'user') and self.request.user.is_authenticated else 1
            pedido.fecha_pedido = timezone.now()
            pedido.estado_pedido = 'PENDIENTE'
            pedido.total_pedido = 0  # Se calculará con los detalles
            pedido.save()
            
            messages.success(
                self.request,
                f"Pedido {pedido.numero_pedido} creado exitosamente. Ahora agregue los productos."
            )
            
            # Redirigir al detalle para agregar productos
            return redirect('ventas:pedido_detail', pk=pedido.pk)
            
        except ValidationError as e:
            messages.error(self.request, f"Error de validación: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al crear el pedido: {str(e)}")
            return self.form_invalid(form)


class PedidoUpdateView(UpdateView):
    model = Pedido
    template_name = 'ventas/pedido_form.html'
    form_class = PedidoForm
    success_url = reverse_lazy('ventas:pedido_list')

    def get_queryset(self):
        return Pedido.objects.filter(deleted_at__isnull=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Pedido'
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )

        # Verificar si se puede modificar
        if not self.get_object().puede_modificarse():
            messages.warning(
                self.request,
                "Este pedido no puede modificarse por su estado actual"
            )

        return context

    def form_valid(self, form):
        try:
            pedido = self.get_object()
            
            if not pedido.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar un pedido en estado {pedido.estado_pedido}"
                )
                return self.form_invalid(form)
            
            pedido = form.save(commit=False)
            pedido.updated_at = timezone.now()
            pedido.save()
            
            messages.success(
                self.request,
                f"Pedido {pedido.numero_pedido} actualizado correctamente"
            )
            return redirect(self.success_url)
            
        except ValidationError as e:
            messages.error(self.request, f"Error de validación: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar: {str(e)}")
            return self.form_invalid(form)


class PedidoDeleteView(View):
    """Soft delete con validaciones"""
    
    def post(self, request, pk):
        try:
            pedido = get_object_or_404(
                Pedido,
                pk=pk,
                deleted_at__isnull=True
            )
            
            if not pedido.puede_eliminarse():
                if pedido.estado_pedido != 'PENDIENTE':
                    messages.error(
                        request,
                        f"Solo se pueden eliminar pedidos PENDIENTE. Estado: {pedido.estado_pedido}"
                    )
                else:
                    messages.error(
                        request,
                        "No se puede eliminar porque tiene productos agregados"
                    )
                return redirect('ventas:pedido_list')
            
            pedido.delete()
            messages.success(
                request,
                f"Pedido {pedido.numero_pedido} eliminado correctamente"
            )
            return redirect('ventas:pedido_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:pedido_list')
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
            return redirect('ventas:pedido_list')


class PedidoDetailView(DetailView):
    model = Pedido
    template_name = 'ventas/pedido_detail.html'
    context_object_name = 'pedido'

    def get_queryset(self):
        return Pedido.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = self.get_object()
        
        context['detalles'] = pedido.detallepedido_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        
        context['puede_modificarse'] = pedido.puede_modificarse()
        context['puede_eliminarse'] = pedido.puede_eliminarse()
        
        return context


class PedidoAgregarProductoView(View):
    """Agregar producto al pedido"""
    
    def post(self, request, pk):
        try:
            pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
            
            if not pedido.puede_modificarse():
                return JsonResponse({
                    'success': False,
                    'error': f"El pedido está en estado {pedido.estado_pedido}"
                }, status=400)
            
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = int(data.get('cantidad', 1))
            precio_unitario = Decimal(data.get('precio_unitario', 0))
            
            producto = get_object_or_404(Producto, pk=producto_id)
            
            # Crear o actualizar detalle
            detalle, created = DetallePedido.objects.get_or_create(
                pedido=pedido,
                producto=producto,
                defaults={
                    'cantidad': cantidad,
                    'precio_unitario': precio_unitario,
                }
            )
            
            if not created:
                detalle.cantidad += cantidad
                detalle.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Producto agregado al pedido',
                'total': float(pedido.total_pedido)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class PedidoCambiarEstadoView(View):
    """Cambiar estado del pedido"""
    
    def post(self, request, pk):
        try:
            pedido = get_object_or_404(Pedido, pk=pk, deleted_at__isnull=True)
            data = json.loads(request.body)
            nuevo_estado = data.get('estado')
            
            pedido.cambiar_estado(nuevo_estado, request.user)
            
            messages.success(
                request,
                f"Pedido {pedido.numero_pedido} cambiado a {nuevo_estado}"
            )
            
            return redirect('ventas:pedido_detail', pk=pk)
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('ventas:pedido_detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:pedido_detail', pk=pk)
        
# ============================================================================
# VENTAS 
# ============================================================================
class VentaListView(ListView):
    model = Ventas
    template_name = 'ventas/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 10

    def get_queryset(self):
        queryset = Ventas.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario', 'metodo_pago', 'pedido')

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

        return queryset.order_by('-fecha_venta', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        context['estados'] = ['PENDIENTE', 'COMPLETADA', 'CANCELADA']
        context['titulo'] = 'Ventas'
        return context


class VentaCreateView(CreateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm
    success_url = reverse_lazy('ventas:venta_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Venta'
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        context['pedidos'] = Pedido.objects.filter(
            estado_pedido='COMPLETADO',
            deleted_at__isnull=True
        )
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                venta = form.save(commit=False)
                venta.usuario_id = self.request.user.id if hasattr(self.request, 'user') and self.request.user.is_authenticated else 1
                venta.fecha_venta = timezone.now()
                venta.estado_venta = 'PENDIENTE'
                venta.save()
                
                messages.success(
                    self.request,
                    f"Venta {venta.numero_factura} creada. Agregue los productos."
                )
                
                return redirect('ventas:venta_detail', pk=venta.pk)
                
        except ValidationError as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al crear: {str(e)}")
            return self.form_invalid(form)
        

class VentaUpdateView(UpdateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    form_class = VentaForm
    success_url = reverse_lazy('ventas:venta_list')

    def get_queryset(self):
        return Ventas.objects.filter(deleted_at__isnull=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Venta'

        if not self.get_object().puede_modificarse():
            messages.warning(
                self.request,
                "Esta venta no puede modificarse"
            )
        return context

    def form_valid(self, form):
        try:
            venta = self.get_object()
            
            if not venta.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar una venta {venta.estado_venta}"
                )
                return self.form_invalid(form)
            
            venta = form.save(commit=False)
            venta.updated_at = timezone.now()
            venta.save()
            
            messages.success(self.request, "Venta actualizada correctamente")
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        

class VentaDeleteView(View):
    def post(self, request, pk):
        try:
            venta = get_object_or_404(Ventas, pk=pk, deleted_at__isnull=True)
            
            if not venta.puede_eliminarse():
                messages.error(
                    request,
                    f"Solo se pueden eliminar ventas PENDIENTE"
                )
                return redirect('ventas:venta_list')
            
            venta.delete()
            messages.success(request, "Venta eliminada correctamente")
            return redirect('ventas:venta_list')
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:venta_list')
        

class VentaDetailView(DetailView):
    model = Ventas
    template_name = 'ventas/venta_detail.html'
    context_object_name = 'venta'

    def get_queryset(self):
        return Ventas.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venta = self.get_object()
        
        context['detalles'] = venta.detalleventa_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        
        return context

class VentaCompletarView(View):
    """Completar venta y actualizar inventario"""
    
    def post(self, request, pk):
        try:
            venta = get_object_or_404(Ventas, pk=pk, deleted_at__isnull=True)
            
            if venta.estado_venta != 'PENDIENTE':
                messages.error(
                    request,
                    "Solo se pueden completar ventas pendientes"
                )
                return redirect('ventas:venta_detail', pk=pk)
            
            with transaction.atomic():
                # Completar venta
                venta.completar_venta()
                
                # TODO: Actualizar inventario aquí
                # for detalle in venta.detalleventa_set.all():
                #     inventario = Inventario.objects.filter(
                #         producto=detalle.producto
                #     ).first()
                #     if inventario:
                #         inventario.cantidad_disponible -= detalle.cantidad
                #         inventario.save()
                
                messages.success(
                    request,
                    f"Venta {venta.numero_factura} completada exitosamente"
                )
            
            return redirect('ventas:venta_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:venta_detail', pk=pk)
        

# ============================================================================
# COTIZACIONES
# ============================================================================
class CotizacionListView(ListView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_list.html'
    context_object_name = 'cotizaciones'
    paginate_by = 10

    def get_queryset(self):
        queryset = Cotizaciones.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

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
        return queryset.order_by('-fecha_cotizacion', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        context['estados'] = ['borrador', 'enviada', 'aceptada', 'rechazada', 'vencida', 'cancelada']
        context['titulo'] = 'Cotizaciones'
        return context


class CotizacionCreateView(CreateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class = CotizacionForm
    success_url = reverse_lazy('ventas:cotizacion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Cotización'
        context['clientes'] = Clientes.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        return context

    def form_valid(self, form):
        try:
            cotizacion = form.save(commit=False)
            cotizacion.usuario_id = self.request.user.id if hasattr(self.request, 'user') and self.request.user.is_authenticated else 1
            cotizacion.fecha_cotizacion = timezone.now().date()
            cotizacion.estado = 'borrador'
            cotizacion.save()
            
            messages.success(
                self.request,
                f"Cotización {cotizacion.numero_cotizacion} creada"
            )
            
            return redirect('ventas:cotizacion_detail', pk=cotizacion.pk)
            
        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        

class CotizacionUpdateView(UpdateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    form_class = CotizacionForm
    success_url = reverse_lazy('ventas:cotizacion_list')

    def get_queryset(self):
        return Cotizaciones.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cotización'
        if not self.get_object().puede_modificarse():
            messages.warning(
                self.request,
                "Esta cotización no puede modificarse"
            )

        return context

    def form_valid(self, form):
        try:
            cotizacion = self.get_object()
            
            if not cotizacion.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar una cotización {cotizacion.estado}"
                )
                return self.form_invalid(form)
            
            cotizacion = form.save(commit=False)
            cotizacion.updated_at = timezone.now()
            cotizacion.save()
            
            messages.success(self.request, "Cotización actualizada")
            return redirect(self.success_url)
            
        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class CotizacionDeleteView(View):
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(
                Cotizaciones,
                pk=pk,
                deleted_at__isnull=True
            )
            
            if not cotizacion.puede_eliminarse():
                messages.error(
                    request,
                    "Solo se pueden eliminar cotizaciones en borrador"
                )
                return redirect('ventas:cotizacion_list')
            
            cotizacion.delete()
            messages.success(request, "Cotización eliminada")
            return redirect('ventas:cotizacion_list')
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_list')
        

class CotizacionDetailView(DetailView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_detail.html'
    context_object_name = 'cotizacion'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return Cotizaciones.objects.filter(
            deleted_at__isnull=True
        ).select_related('cliente', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cotizacion = self.get_object()
        
        context['detalles'] = cotizacion.detallecotizacion_set.filter(
            deleted_at__isnull=True
        ).select_related('producto')
        
        return context


class CotizacionEnviarView(View):
    """Enviar cotización al cliente"""
    
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk)
            
            if cotizacion.estado != 'borrador':
                messages.error(request, "Solo se pueden enviar cotizaciones en borrador")
                return redirect('ventas:cotizacion_detail', pk=pk)
            
            cotizacion.estado = 'enviada'
            cotizacion.save()
            
            # TODO: Enviar email al cliente
            messages.success(
                request,
                f"Cotización {cotizacion.numero_cotizacion} enviada"
            )
            
            return redirect('ventas:cotizacion_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)


class CotizacionAceptarView(View):
    """Aceptar cotización"""
    
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk)
            
            if cotizacion.estado != 'enviada':
                messages.error(request, "Solo se pueden aceptar cotizaciones enviadas")
                return redirect('ventas:cotizacion_detail', pk=pk)
            
            cotizacion.estado = 'aceptada'
            cotizacion.save()
            
            messages.success(
                request,
                f"Cotización {cotizacion.numero_cotizacion} aceptada"
            )
            
            return redirect('ventas:cotizacion_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)

class CotizacionConvertirVentaView(View):
    """Convertir cotización en venta"""
    
    def post(self, request, pk):
        try:
            cotizacion = get_object_or_404(Cotizaciones, pk=pk)
            
            puede, mensaje = cotizacion.puede_convertirse_en_venta()
            if not puede:
                messages.error(request, mensaje)
                return redirect('ventas:cotizacion_detail', pk=pk)
            
            with transaction.atomic():
                venta = cotizacion.convertir_en_venta(request.user)
                
                messages.success(
                    request,
                    f"Cotización convertida en venta {venta.numero_factura}"
                )
            
            return redirect('ventas:venta_detail', pk=venta.pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('ventas:cotizacion_detail', pk=pk)

# Carrito
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from inventario.models import Producto, Inventario
from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_GET

IVA_RATE = Decimal('0.19')

def get_or_create_carrito(request):
    """Obtiene o crea carrito para usuario autenticado o sesión anónima"""
    
    if request.user.is_authenticated:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        
        if not cliente and request.user.email:
            cliente = Clientes.objects.create(
                nombre=request.user.get_full_name() or request.user.username,
                email=request.user.email,
                fecha_registro=timezone.now()
            )
        
        if cliente:
            carrito, created = Carritos.objects.get_or_create(
                cliente=cliente,
                deleted_at__isnull=True,
                defaults={'created_at': timezone.now()}
            )
            return carrito
    
    # Para usuarios no autenticados → session_id
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
        request.session.save()
    
    carrito, created = Carritos.objects.get_or_create(
        session_id=session_id,
        deleted_at__isnull=True,
        defaults={'created_at': timezone.now()}
    )
    return carrito


@login_required
def carrito_compra(request):
    carrito = get_or_create_carrito(request)
    items_qs = ItemsCarrito.objects.filter(carrito=carrito).select_related('producto')
    
    items = []
    total_carrito = Decimal('0')
    total_iva = Decimal('0') 
    
    for item in items_qs:
        precio = Decimal(str(item.precio_unitario))
        cantidad = Decimal(str(item.cantidad))
        
        # CALCULAR IVA POR UNIDAD 
        iva_por_unidad = precio * IVA_RATE  
        subtotal_linea = precio * cantidad   
        iva_total_linea = iva_por_unidad * cantidad
        
        items.append({
            'producto_id': item.producto.id_producto,
            'nombre': item.producto.referencia_producto or item.producto.codigo_producto,
            'sku': item.producto.codigo_producto,
            'precio_base': float(precio),
            'iva_unitario': float(iva_por_unidad),
            'cantidad': int(cantidad),
            'subtotal': float(subtotal_linea),
            'iva': float(iva_total_linea),
            'imagen_url': item.producto.get_imagen_principal().ruta_imagen 
                        if hasattr(item.producto, 'get_imagen_principal') 
                        and item.producto.get_imagen_principal() 
                        else '/static/img/placeholder.jpg',
            'stock': item.producto.get_stock_total() if hasattr(item.producto, 'get_stock_total') else 999,
            'item_id': item.id_item,
        })
        total_carrito += subtotal_linea
        total_iva += iva_total_linea 
    context = {
        'carrito_items': items,
        'carrito_cantidad': sum(i['cantidad'] for i in items), 
        'total_carrito': float(total_carrito),
        'total_iva': float(total_iva),
        'carrito_items_json': items,
    }
    
    return render(request, 'pagina/carrito.html', context)


@require_POST
def api_carrito_agregar(request):
    try:
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        producto = Producto.objects.get(id_producto=producto_id)
        carrito = get_or_create_carrito(request)
        
        # Verificar stock
        stock_disponible = producto.get_stock_total() if hasattr(producto, 'get_stock_total') else 999
        if stock_disponible < cantidad:
            return JsonResponse({
                'success': False,
                'error': f'Solo hay {stock_disponible} unidades disponibles'
            }, status=400)
        
        precio_unitario = Decimal(str(producto.precio_actual))
        
        item, created = ItemsCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={
                'precio_unitario': producto.precio_actual,
                'cantidad': cantidad,
                'created_at': timezone.now()
            }
        )
        
        if not created:
            item.cantidad += cantidad
            item.updated_at = timezone.now()
            item.save()
        
        total_items = ItemsCarrito.objects.filter(
            carrito=carrito
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'cantidad_total': total_items,
            'mensaje': f'{producto.referencia_producto} × {cantidad} añadido'
        })
        
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        import traceback
        print(f"❌ Error en api_carrito_agregar: {e}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def api_carrito_eliminar(request, item_id):
    try:
        carrito = get_or_create_carrito(request)
        item = get_object_or_404(ItemsCarrito, id_item=item_id, carrito=carrito)
        item.delete()
        
        total_items = ItemsCarrito.objects.filter(
            carrito=carrito
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'cantidad_total': total_items
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def api_carrito_actualizar(request, item_id):
    try:
        carrito = get_or_create_carrito(request)
        item = get_object_or_404(ItemsCarrito, id_item=item_id, carrito=carrito)
        
        nueva_cantidad = int(request.POST.get('cantidad', item.cantidad))
        
        if nueva_cantidad < 1:
            item.delete()
        else:
            stock = item.producto.get_stock_total() if hasattr(item.producto, 'get_stock_total') else 999
            if nueva_cantidad > stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Solo hay {stock} unidades disponibles'
                }, status=400)
            item.cantidad = nueva_cantidad
            item.updated_at = timezone.now()
            item.save()
        
        total_items = ItemsCarrito.objects.filter(
            carrito=carrito
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'cantidad_total': total_items
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_GET
def api_carrito_contador(request):
    """API endpoint para obtener la cantidad del carrito (AJAX)"""
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
        print(f" Error en api_carrito_contador: {e}")
    
    return JsonResponse({'cantidad': carrito_cantidad})
#  VISTA PRINCIPAL DEL PERFIL

@login_required
def perfil_usuario(request):
    """Vista principal del perfil de usuario"""
    
    # Obtener cliente asociado al usuario
    cliente = Clientes.objects.filter(
        email=request.user.email,
        deleted_at__isnull=True
    ).first()
    
    # Stats del usuario
    total_pedidos = Pedido.objects.filter(cliente=cliente).count() if cliente else 0
    wishlist_count = 0  # Implementar si tienes modelo de favoritos
    
    # Puntos de lealtad (ejemplo simple)
    puntos_lealtad = (total_pedidos * 100) if cliente else 0
    
    # Gamificación
    user_level = min(10, (puntos_lealtad // 500) + 1)
    xp_current = puntos_lealtad % 500
    xp_next = 500
    xp_percent = (xp_current / xp_next) * 100
    xp_to_next = xp_next - xp_current
    
    # Pedidos recientes
    pedidos_recientes = []
    if cliente:
        pedidos_qs = Pedido.objects.filter(cliente=cliente).order_by('-fecha_pedido')[:5]
        for p in pedidos_qs:
            pedidos_recientes.append({
                'id': p.id_pedido if hasattr(p, 'id_pedido') else p.pk,
                'numero': p.numero_pedido if hasattr(p, 'numero_pedido') else f'ORD-{p.pk}',
                'fecha': p.fecha_pedido,
                'estado': p.estado_pedido if hasattr(p, 'estado_pedido') else 'PENDIENTE',
                'estado_color': 'success' if p.estado_pedido == 'COMPLETADO' else 'warning',
                'total': p.total if hasattr(p, 'total') else 0,
                'total_items': 3,  # Calcular desde DetallePedido si existe
                'progreso_percent': {'PENDIENTE': 25, 'CONFIRMADO': 50, 'EN PROCESO': 75, 'COMPLETADO': 100}.get(p.estado_pedido, 25),
                'estado_detalle': {'PENDIENTE': 'Esperando confirmación', 'CONFIRMADO': 'Preparando envío', 'EN PROCESO': 'En camino', 'COMPLETADO': 'Entregado'}.get(p.estado_pedido, 'Procesando'),
                'puede_rastrear': p.estado_pedido in ['EN PROCESO', 'CONFIRMADO']
            })
    
    # Badges/Gamification
    badges_count = min(5, total_pedidos // 2)
    
    # Notificaciones nuevas
    notificaciones_nuevas = 0  # Implementar si tienes modelo de notificaciones
    
    context = {
        'cliente': cliente,
        'total_pedidos': total_pedidos,
        'wishlist_count': wishlist_count,
        'puntos_lealtad': puntos_lealtad,
        'badges_count': badges_count,
        'user_level': user_level,
        'xp_current': xp_current,
        'xp_next': xp_next,
        'xp_percent': xp_percent,
        'xp_to_next': xp_to_next,
        'pedidos_recientes': pedidos_recientes,
        'notificaciones_nuevas': notificaciones_nuevas,
        'last_password_change': getattr(request.user, 'last_login', 'Nunca'),
    }
    
    return render(request, 'pagina/perfil.html', context)


#  ACTUALIZAR INFORMACIÓN DEL PERFIL

@require_POST
@login_required
def perfil_actualizar(request):
    """Actualizar datos personales del usuario"""
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        
        if not cliente:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrado'}, status=404)
        
        # Actualizar campos permitidos
        if 'nombre' in request.POST:
            nombre_completo = request.POST.get('nombre', '').strip()
            partes = nombre_completo.split(' ', 1)
            request.user.first_name = partes[0]
            request.user.last_name = partes[1] if len(partes) > 1 else ''
            request.user.save()
        
        if 'telefono' in request.POST:
            cliente.telefono = request.POST.get('telefono', '')
        if 'fecha_nacimiento' in request.POST:
            cliente.fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        if 'direccion' in request.POST:
            cliente.direccion = request.POST.get('direccion', '')
        
        cliente.save()
        
        return JsonResponse({'success': True, 'mensaje': 'Perfil actualizado'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


#  ACTUALIZAR AVATAR

@require_POST
@login_required
def avatar_actualizar(request):
    """Actualizar foto de perfil del usuario"""
    try:
        data = json.loads(request.body)
        avatar_url = data.get('avatar_url', '')
        
        # Aquí iría la lógica para guardar la imagen en media/
        # Por ahora, actualizamos un campo hipotético en el modelo User
        # Si tu modelo Usuarios tiene campo 'foto_perfil':
        if hasattr(request.user, 'foto_perfil') and avatar_url:
            # request.user.foto_perfil = avatar_url
            # request.user.save()
            pass
        
        return JsonResponse({'success': True, 'avatar_url': avatar_url})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


#  CAMBIAR CONTRASEÑA

@require_POST
@login_required
def password_cambiar(request):
    """Cambiar contraseña del usuario"""
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        # Verificar contraseña actual
        if not request.user.check_password(current_password):
            return JsonResponse({'success': False, 'error': 'Contraseña actual incorrecta'}, status=400)
        
        # Validar nueva contraseña
        if len(new_password) < 8:
            return JsonResponse({'success': False, 'error': 'La contraseña debe tener al menos 8 caracteres'}, status=400)
        
        # Cambiar contraseña
        request.user.set_password(new_password)
        request.user.save()
        
        # ✅ NO necesitas update_last_login - Django lo hace automáticamente
        # Si quieres forzar la actualización:
        from django.utils import timezone
        request.user.last_login = timezone.now()
        request.user.save()
        
        return JsonResponse({'success': True, 'mensaje': 'Contraseña actualizada'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


#  NOTIFICACIONES

@require_POST
@login_required
def notificaciones_marcar_leidas(request):
    """Marcar todas las notificaciones como leídas"""
    try:
        # Implementar según tu modelo de notificaciones
        # Ejemplo: Notification.objects.filter(usuario=request.user, leida=False).update(leida=True)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ⚙️ PREFERENCIAS

@require_POST
@login_required
def preferencias_guardar(request):
    """Guardar preferencias del usuario"""
    try:
        data = json.loads(request.body)
        # Guardar en un campo JSON o modelo de preferencias
        # request.user.preferencias = data
        # request.user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


#  EXPORTAR DATOS (GDPR)

@require_GET
@login_required
def datos_exportar(request):
    """Exportar datos personales del usuario en formato JSON"""
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        
        datos_usuario = {
            'usuario': {
                'username': request.user.username,
                'email': request.user.email,
                'fecha_registro': request.user.date_joined.isoformat() if hasattr(request.user, 'date_joined') else None,
                'ultimo_acceso': request.user.last_login.isoformat() if request.user.last_login else None,
            },
            'cliente': {
                'nombre': cliente.nombre if cliente else None,
                'telefono': cliente.telefono if cliente else None,
                'direccion': cliente.direccion if cliente else None,
            } if cliente else None,
            'pedidos': list(Pedido.objects.filter(cliente=cliente).values(
                'id_pedido', 'numero_pedido', 'fecha_pedido', 'estado_pedido', 'total'
            ) if cliente else []),
            'exportado_en': timezone.now().isoformat()
        }
        
        import json
        from django.http import HttpResponse
        
        response = HttpResponse(
            json.dumps(datos_usuario, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="order-rae-datos-{timezone.now().date()}.json"'
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

#  STATS EN TIEMPO REAL

@require_GET
@login_required
def perfil_stats(request):
    """API para actualizar stats del perfil en tiempo real"""
    try:
        cliente = Clientes.objects.filter(
            email=request.user.email,
            deleted_at__isnull=True
        ).first()
        
        stats = {
            'pedidos': Pedido.objects.filter(cliente=cliente).count() if cliente else 0,
            'notificaciones_nuevas': 0,  # Implementar según tu modelo
            'puntos_lealtad': (Pedido.objects.filter(cliente=cliente).count() * 100) if cliente else 0,
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)