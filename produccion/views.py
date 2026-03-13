from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Produccion
from inventario.models import Producto, Proveedores
from ventas.models import Pedido
from .forms import ProduccionForm

class ProduccionListView(ListView):
    model = Produccion
    template_name = 'produccion/produccion_list.html'
    context_object_name = 'producciones'
    paginate_by = 10  # Paginación automática

    def get_queryset(self):
        queryset = super().get_queryset()
        
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
                Q(observaciones__icontains=busqueda)
            )
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['productos'] = Producto.objects.all()
        context['estados'] = ['PENDIENTE', 'EN PROCESO', 'TERMINADA', 'CANCELADA']
        return context

class ProduccionCreateView(CreateView):
    model = Produccion
    template_name = 'produccion/produccion_form.html'
    form_class = ProduccionForm
    success_url = reverse_lazy('produccion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Producción'
        context['productos'] = Producto.objects.all()
        context['proveedores'] = Proveedores.objects.all()
        return context

class ProduccionUpdateView(UpdateView):
    model = Produccion
    template_name = 'produccion/produccion_form.html'
    form_class = ProduccionForm
    success_url = reverse_lazy('produccion_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Producción'
        context['productos'] = Producto.objects.all()
        context['proveedores'] = Proveedores.objects.all()
        return context

class ProduccionDeleteView(DeleteView):
    model = Produccion
    template_name = 'produccion/produccion_confirm_delete.html'
    success_url = reverse_lazy('produccion_list')

class ProduccionDetailView(DetailView):
    model = Produccion
    template_name = 'produccion/produccion_detail.html'
    context_object_name = 'item'