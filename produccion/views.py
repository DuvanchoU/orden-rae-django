from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Produccion, DetalleProduccionPedido
from inventario.models import Producto, Proveedores
from ventas.models import Pedido
from .forms import ProduccionForm

class ProduccionListView(ListView):
    model = Produccion
    template_name = 'produccion/produccion_list.html'
    context_object_name = 'producciones'
    paginate_by = 10  

    def get_queryset(self):
        queryset = Produccion.objects.filter(deleted_at__isnull=True).select_related(
            'producto', 'proveedor'
        )
        
        # Obtener parámetros del filtro
        producto_id = self.request.GET.get('producto')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        busqueda = self.request.GET.get('busqueda')

        # Aplicar filtros
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if estado:
            queryset = queryset.filter(estado_produccion=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_inicio__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_fin__lte=fecha_fin)
        if busqueda:
            queryset = queryset.filter(
                Q(producto__codigo_producto__icontains=busqueda) |
                Q(observaciones__icontains=busqueda) |
                Q(producto__referencia_producto__icontains=busqueda)
            )
            
        return queryset.order_by('-fecha_inicio', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['productos'] = Producto.objects.filter(deleted_at__isnull=True)
        context['estados'] = ['PENDIENTE', 'EN PROCESO', 'TERMINADA', 'CANCELADA']
        context['titulo'] = 'Producción'
        return context

class ProduccionCreateView(CreateView):
    model = Produccion
    template_name = 'produccion/produccion_form.html'
    form_class = ProduccionForm
    success_url = reverse_lazy('produccion:produccion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Producción'
        context['productos'] = Producto.objects.filter(deleted_at__isnull=True)
        context['proveedores'] = Proveedores.objects.filter(deleted_at__isnull=True)
        return context
    
    def form_valid(self, form):
        try:
            produccion = form.save(commit=False)
            produccion.created_at = timezone.now()
            produccion.updated_at = timezone.now()
            produccion.save()
            
            messages.success(
                self.request, 
                f'Producción creada exitosamente. Cantidad disponible: {produccion.cantidad_producida} und.'
            )
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al crear: {str(e)}')
            return self.form_invalid(form)
        

class ProduccionUpdateView(UpdateView):
    model = Produccion
    template_name = 'produccion/produccion_form.html'
    form_class = ProduccionForm
    success_url = reverse_lazy('produccion:produccion_list')

    def get_queryset(self):
        return Produccion.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Producción'
        context['productos'] = Producto.objects.filter(deleted_at__isnull=True)
        context['proveedores'] = Proveedores.objects.filter(deleted_at__isnull=True)

        # Alertas de negocio
        obj = self.get_object()
        if not obj.puede_modificarse():
            messages.warning(
                self.request,
                f"Esta producción está {obj.estado_produccion} y no puede modificarse"
            )
        return context

    def form_valid(self, form):
        try:
            produccion = self.get_object()
            
            if not produccion.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar una producción en estado {produccion.estado_produccion}"
                )
                return self.form_invalid(form)
            
            # Validar que la nueva cantidad no sea menor a la asignada
            nueva_cantidad = form.cleaned_data.get('cantidad_producida')
            cantidad_asignada = produccion.get_cantidad_asignada()
            
            if nueva_cantidad < cantidad_asignada:
                messages.error(
                    self.request,
                    f"No se puede reducir la cantidad. Hay {cantidad_asignada} und. asignadas a pedidos"
                )
                return self.form_invalid(form)
            
            produccion = form.save(commit=False)
            produccion.updated_at = timezone.now()
            produccion.save()
            
            messages.success(self.request, 'Producción actualizada correctamente')
            return redirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, f'Error de validación: {str(e)}')
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return self.form_invalid(form)
        

class ProduccionDeleteView(View):
    """Soft delete con validaciones"""
    
    def post(self, request, pk):
        try:
            produccion = get_object_or_404(
                Produccion, 
                pk=pk, 
                deleted_at__isnull=True
            )
            
            if not produccion.puede_eliminarse():
                if produccion.estado_produccion != 'PENDIENTE':
                    messages.error(
                        request,
                        f"Solo se pueden eliminar producciones PENDIENTE. Estado actual: {produccion.estado_produccion}"
                    )
                else:
                    messages.error(
                        request,
                        "No se puede eliminar porque tiene detalles asignados a pedidos"
                    )
                return redirect('produccion:produccion_list')
            
            produccion.delete()  # Soft delete
            messages.success(request, 'Producción eliminada correctamente')
            return redirect('produccion:produccion_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
            return redirect('produccion:produccion_list')
        

class ProduccionDetailView(DetailView):
    model = Produccion
    template_name = 'produccion/produccion_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return Produccion.objects.filter(
            deleted_at__isnull=True
        ).select_related('producto', 'proveedor')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        produccion = self.get_object()
        
        context['cantidad_asignada'] = produccion.get_cantidad_asignada()
        context['cantidad_disponible'] = produccion.get_cantidad_disponible()
        context['esta_completamente_asignada'] = produccion.esta_completamente_asignada()
        context['detalles'] = produccion.detalleproduccionpedido_set.filter(
            deleted_at__isnull=True
        ).select_related('pedido', 'producto')
        
        return context