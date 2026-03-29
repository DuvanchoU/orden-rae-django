from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from .models import Compras, DetalleCompra
from inventario.models import Proveedores, Producto
from usuarios.models import Usuarios
from .forms import CompraForm, DetalleCompraForm
import json


# ============================================================================
# COMPRAS 
# ============================================================================
class CompraListView(ListView):
    model = Compras
    template_name = 'compras/compra_list.html'
    context_object_name = 'compras'
    paginate_by = 10

    def get_queryset(self):
        queryset = Compras.objects.filter(
            deleted_at__isnull=True
        ).select_related('proveedor', 'usuario')

        proveedor = self.request.GET.get('proveedor')
        estado = self.request.GET.get('estado')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        busqueda = self.request.GET.get('busqueda')

        if proveedor:
            queryset = queryset.filter(proveedor_id=proveedor)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_compra__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_compra__lte=fecha_fin)
        if busqueda:
            queryset = queryset.filter(
                Q(proveedor__nombre__icontains=busqueda) |
                Q(observaciones__icontains=busqueda)
            )
        return queryset.order_by('-fecha_compra', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedores.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        context['estados'] = ['PENDIENTE', 'RECIBIDA', 'CANCELADA']
        context['titulo'] = 'Compras'

        # Estadísticas
        context['total_compras'] = Compras.objects.filter(
            deleted_at__isnull=True
        ).count()
        context['compras_pendientes'] = Compras.objects.filter(
            estado='PENDIENTE',
            deleted_at__isnull=True
        ).count()
        
        return context


class CompraCreateView(CreateView):
    model = Compras
    template_name = 'compras/compra_form.html'
    form_class = CompraForm
    success_url = reverse_lazy('compras:compra_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Compra'
        context['proveedores'] = Proveedores.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        return context

    def form_valid(self, form):
        try:
            # Validar que el proveedor esté activo
            proveedor = form.cleaned_data['proveedor']
            if proveedor.estado != 'ACTIVO':
                messages.error(
                    self.request,
                    "El proveedor seleccionado está inactivo"
                )
                return self.form_invalid(form)
            
            compra = form.save(commit=False)
            compra.usuario_id = self.request.user.id if hasattr(self.request, 'user') and self.request.user.is_authenticated else 1
            compra.fecha_compra = timezone.now().date()
            compra.estado = 'PENDIENTE'
            compra.total_compra = 0 
            compra.save()
            
            messages.success(
                self.request,
                f"Compra #{compra.id_compra} creada. Ahora agregue los productos."
            )
            
            return redirect('compras:compra_detail', pk=compra.pk)
            
        except ValidationError as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al crear: {str(e)}")
            return self.form_invalid(form)


class CompraUpdateView(UpdateView):
    model = Compras
    template_name = 'compras/compra_form.html'
    form_class = CompraForm
    success_url = reverse_lazy('compras:compra_list')

    def get_queryset(self):
        return Compras.objects.filter(deleted_at__isnull=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Compra'
        context['proveedores'] = Proveedores.objects.filter(
            estado='ACTIVO',
            deleted_at__isnull=True
        )
        
        if not self.get_object().puede_modificarse():
            messages.warning(
                self.request,
                "Esta compra no puede modificarse por su estado actual"
            )
        
        return context

    def form_valid(self, form):
        try:
            compra = self.get_object()
            
            if not compra.puede_modificarse():
                messages.error(
                    self.request,
                    f"No se puede modificar una compra {compra.estado}"
                )
                return self.form_invalid(form)
            
            compra = form.save(commit=False)
            compra.updated_at = timezone.now()
            compra.save()
            
            messages.success(
                self.request,
                f"Compra #{compra.id_compra} actualizada correctamente"
            )
            return redirect(self.success_url)
            
        except ValidationError as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error al actualizar: {str(e)}")
            return self.form_invalid(form)


class CompraDeleteView(View):
    """Soft delete con validaciones"""
    
    def post(self, request, pk):
        try:
            compra = get_object_or_404(
                Compras,
                pk=pk,
                deleted_at__isnull=True
            )
            
            if not compra.puede_eliminarse():
                messages.error(
                    request,
                    f"Solo se pueden eliminar compras PENDIENTE. Estado: {compra.estado}"
                )
                return redirect('compras:compra_list')
            
            compra.delete()
            messages.success(
                request,
                f"Compra #{compra.id_compra} eliminada correctamente"
            )
            return redirect('compras:compra_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('compras:compra_list')
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('compras:compra_list')


class CompraDetailView(DetailView):
    model = Compras
    template_name = 'compras/compra_detail.html'
    context_object_name = 'compra'
    
    def get_queryset(self):
        return Compras.objects.filter(
            deleted_at__isnull=True
        ).select_related('proveedor', 'usuario')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar productos del detalle de compra si existen
        compra = self.get_object()

        context['detalles'] = compra.detallecompra_set.all().select_related('producto')
        
        context['puede_modificarse'] = compra.puede_modificarse()
        context['puede_recibirse'] = compra.puede_recibirse()
        context['total_productos'] = compra.get_cantidad_productos()
        
        return context


class CompraAgregarProductoView(View):
    """Agregar producto a la compra"""
    
    def post(self, request, pk):
        try:
            compra = get_object_or_404(Compras, pk=pk, deleted_at__isnull=True)
            
            if not compra.puede_modificarse():
                return JsonResponse({
                    'success': False,
                    'error': f"La compra está en estado {compra.estado}"
                }, status=400)
            
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = int(data.get('cantidad', 1))
            precio_unitario = Decimal(data.get('precio_unitario', 0))
            
            producto = get_object_or_404(Producto, pk=producto_id)
            
            # Agregar producto
            detalle = compra.agregar_producto(
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Producto agregado',
                'subtotal': float(detalle.subtotal),
                'total': float(compra.total_compra)
            })
            
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class CompraRecibirView(View):
    """Marcar compra como recibida y actualizar inventario"""
    
    def post(self, request, pk):
        try:
            compra = get_object_or_404(Compras, pk=pk, deleted_at__isnull=True)
            
            if not compra.puede_recibirse():
                messages.error(
                    request,
                    "La compra no puede ser recibida. Verifique que tenga productos y esté pendiente"
                )
                return redirect('compras:compra_detail', pk=pk)
            
            with transaction.atomic():
                compra.recibir_compra()
            
            messages.success(
                request,
                f"Compra #{compra.id_compra} recibida. Inventario actualizado."
            )
            return redirect('compras:compra_detail', pk=pk)
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('compras:compra_detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('compras:compra_detail', pk=pk)


class CompraCancelarView(View):
    """Cancelar compra"""
    
    def post(self, request, pk):
        try:
            compra = get_object_or_404(Compras, pk=pk, deleted_at__isnull=True)
            
            if compra.estado != 'PENDIENTE':
                messages.error(
                    request,
                    f"Solo se pueden cancelar compras PENDIENTE"
                )
                return redirect('compras:compra_detail', pk=pk)
            
            compra.cancelar_compra()
            
            messages.success(
                request,
                f"Compra #{compra.id_compra} cancelada"
            )
            return redirect('compras:compra_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('compras:compra_detail', pk=pk)
    
# ============================================================================
# DETALLE COMPRA
# ============================================================================
class DetalleCompraCreateView(CreateView):
    model = DetalleCompra
    template_name = 'compras/detalle_compra_form.html'
    fields = ['compra', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    success_url = reverse_lazy('compras:compra_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Agregar Producto a Compra'
        context['compras'] = Compras.objects.filter(
            estado='PENDIENTE',
            deleted_at__isnull=True
        )
        context['productos'] = Producto.objects.filter(
            deleted_at__isnull=True
        )
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Filtrar compras pendientes
        if 'data' in kwargs:
            compra_id = kwargs['data'].get('compra')
            if compra_id:
                kwargs['queryset_compra'] = Compras.objects.filter(
                    pk=compra_id,
                    estado='PENDIENTE',
                    deleted_at__isnull=True
                )
        
        return kwargs

    def form_valid(self, form):
        try:
            detalle = form.save(commit=False)
            
            # Validar que la compra pueda modificarse
            if not detalle.compra.puede_modificarse():
                messages.error(
                    self.request,
                    f"La compra #{detalle.compra.id_compra} no puede modificarse"
                )
                return self.form_invalid(form)
            
            detalle.save()
            
            messages.success(
                self.request,
                f"Producto agregado a la compra #{detalle.compra.id_compra}"
            )
            
            return redirect('compras:compra_detail', pk=detalle.compra.pk)
            
        except ValidationError as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class DetalleCompraDeleteView(View):
    """Eliminar detalle de compra"""
    
    def post(self, request, pk):
        try:
            detalle = get_object_or_404(DetalleCompra, pk=pk)
            compra = detalle.compra
            
            if not compra.puede_modificarse():
                messages.error(
                    request,
                    f"No se puede modificar la compra #{compra.id_compra}"
                )
                return redirect('compras:compra_detail', pk=compra.pk)
            
            detalle.delete()
            
            messages.success(
                request,
                "Producto eliminado de la compra"
            )
            return redirect('compras:compra_detail', pk=compra.pk)
            
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('compras:compra_list')