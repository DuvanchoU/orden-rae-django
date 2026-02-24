from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from .models import Clientes, Pedido, Ventas, Cotizaciones, DetalleVenta, DetalleCotizacion
from inventario.models import Producto
from usuarios.models import Usuarios
from django.contrib import messages
from django.utils import timezone

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
    fields = ['nombre', 'apellido', 'telefono', 'email', 'direccion', 'estado']
    success_url = reverse_lazy('ventas:cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Cliente'
        return context


class ClienteUpdateView(UpdateView):
    model = Clientes
    template_name = 'ventas/cliente_form.html'
    fields = ['nombre', 'apellido', 'telefono', 'email', 'direccion', 'estado']
    success_url = reverse_lazy('ventas:cliente_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cliente'
        return context


class ClienteDeleteView(DeleteView):
    model = Clientes
    template_name = 'ventas/cliente_confirm_delete.html'
    success_url = reverse_lazy('ventas:cliente_list')


# PEDIDOS
class PedidoListView(ListView):
    model = Pedido
    template_name = 'ventas/pedido_list.html'
    context_object_name = 'pedido'
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
            queryset = queryset.filter(estado_pedido=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_pedido__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_pedido__lte=fecha_fin)
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
    fields = ['cliente', 'fecha_entrega_estimada', 'direccion_entrega', 'estado_pedido', 'observaciones']
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
    fields = ['cliente', 'fecha_entrega_estimada', 'direccion_entrega', 'estado_pedido', 'observaciones']
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
        context['estados'] = ['PENDIENTE', 'PAGADA', 'FACTURADA', 'CANCELADA']
        return context


class VentaCreateView(CreateView):
    model = Ventas
    template_name = 'ventas/venta_form.html'
    fields = ['cliente', 'pedido', 'tipo_venta', 'subtotal', 'impuesto', 'descuento', 
              'total', 'estado_venta', 'metodo_pago', 'observaciones']
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
    fields = ['cliente', 'pedido', 'tipo_venta', 'subtotal', 'impuesto', 'descuento', 
              'total', 'estado_venta', 'metodo_pago', 'observaciones']
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
        busqueda = self.request.GET.get('busqueda')

        if cliente:
            queryset = queryset.filter(cliente_id=cliente)
        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(numero_cotizacion__icontains=busqueda)
        return queryset.order_by('-fecha_cotizacion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clientes'] = Clientes.objects.all()
        context['estados'] = ['PENDIENTE', 'APROBADA', 'RECHAZADA', 'EXPIRADA']
        return context


class CotizacionCreateView(CreateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    fields = ['numero_cotizacion', 'cliente', 'fecha_vencimiento', 'estado', 
              'tiempo_entrega', 'observaciones', 'subtotal', 'impuesto', 'descuento', 'total']
    success_url = reverse_lazy('ventas:cotizacion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Cotización'
        context['clientes'] = Clientes.objects.all()
        return context


class CotizacionUpdateView(UpdateView):
    model = Cotizaciones
    template_name = 'ventas/cotizacion_form.html'
    fields = ['numero_cotizacion', 'cliente', 'fecha_vencimiento', 'estado', 
              'tiempo_entrega', 'observaciones', 'subtotal', 'impuesto', 'descuento', 'total']
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