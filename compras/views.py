from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from .models import Compras, DetalleCompra
from inventario.models import Proveedores, Producto
from usuarios.models import Usuarios
from django.utils import timezone


# COMPRAS
class CompraListView(ListView):
    model = Compras
    template_name = 'compras/compra_list.html'
    context_object_name = 'compras'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
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
        return queryset.order_by('-fecha_compra')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proveedores'] = Proveedores.objects.all()
        context['estados'] = ['PENDIENTE', 'APROBADA', 'RECIBIDA', 'CANCELADA']
        return context


class CompraCreateView(CreateView):
    model = Compras
    template_name = 'compras/compra_form.html'
    fields = ['proveedor', 'fecha_compra', 'total_compra', 'estado', 'foto_orden', 'observaciones']
    success_url = reverse_lazy('compras:compra_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Compra'
        context['proveedores'] = Proveedores.objects.all()
        return context

    def form_valid(self, form):
        form.instance.usuario_id = 1  # Cambiar por request.user.id
        return super().form_valid(form)


class CompraUpdateView(UpdateView):
    model = Compras
    template_name = 'compras/compra_form.html'
    fields = ['proveedor', 'fecha_compra', 'total_compra', 'estado', 'foto_orden', 'observaciones']
    success_url = reverse_lazy('compras:compra_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Compra'
        context['proveedores'] = Proveedores.objects.all()
        return context


class CompraDeleteView(DeleteView):
    model = Compras
    template_name = 'compras/compra_confirm_delete.html'
    success_url = reverse_lazy('compras:compra_list')

# DETALLE COMPRA
class DetalleCompraCreateView(CreateView):
    model = DetalleCompra
    template_name = 'compras/detalle_compra_form.html'
    fields = ['compra', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    success_url = reverse_lazy('compras:compra_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Agregar Producto a Compra'
        context['compras'] = Compras.objects.all()
        context['productos'] = Producto.objects.all()
        return context