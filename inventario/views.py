from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Producto, Bodegas, Categorias, Proveedores, Inventario
from django.contrib import messages
from .forms import InventarioForm, ProductoForm, BodegaForm, CategoriaForm, ProveedorForm

# PRODUCTOS
class ProductoListView(ListView):
    model = Producto
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        
        categoria = self.request.GET.get('categoria')
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(codigo_producto__icontains=busqueda) |
                Q(referencia_producto__icontains=busqueda) |
                Q(color_producto__icontains=busqueda)
            )
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categorias.objects.all()
        context['estados'] = ['DISPONIBLE', 'AGOTADO']
        return context


class ProductoCreateView(CreateView):
    model = Producto
    template_name = 'inventario/producto_create.html'
    form_class = ProductoForm 
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Producto'
        context['categorias'] = Categorias.objects.all()
        return context


class ProductoUpdateView(UpdateView):
    model = Producto
    template_name = 'inventario/producto_create.html'
    form_class = ProductoForm 
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Producto'
        context['categorias'] = Categorias.objects.all()
        return context


class ProductoDeleteView(DeleteView):
    model = Producto
    template_name = 'inventario/producto_confirm_delete.html'
    success_url = reverse_lazy('inventario:producto_list')

class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'inventario/producto_detail.html'
    context_object_name = 'producto'

# BODEGAS
class BodegaListView(ListView):
    model = Bodegas
    template_name = 'inventario/bodega_list.html'
    context_object_name = 'bodegas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(nombre_bodega__icontains=busqueda) |
                Q(direccion__icontains=busqueda)
            )
            
        return queryset.order_by('nombre_bodega')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = ['ACTIVA', 'INACTIVA']
        return context


class BodegaCreateView(CreateView):
    model = Bodegas
    template_name = 'inventario/bodega_form.html'
    form_class = BodegaForm
    success_url = reverse_lazy('inventario:bodega_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Bodega'
        return context


class BodegaUpdateView(UpdateView):
    model = Bodegas
    template_name = 'inventario/bodega_form.html'
    form_class = BodegaForm
    success_url = reverse_lazy('inventario:bodega_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Bodega'
        return context


class BodegaDeleteView(DeleteView):
    model = Bodegas
    template_name = 'inventario/bodega_confirm_delete.html'
    success_url = reverse_lazy('inventario:bodega_list')


# CATEGORÍAS
class CategoriaListView(ListView):
    model = Categorias
    template_name = 'inventario/categoria_list.html'
    context_object_name = 'categorias'
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if estado:
            queryset = queryset.filter(estado_categoria=estado)
        if busqueda:
            queryset = queryset.filter(nombre_categoria__icontains=busqueda)
            
        return queryset.order_by('nombre_categoria')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = ['activo', 'inactivo']
        return context


class CategoriaCreateView(CreateView):
    model = Categorias
    template_name = 'inventario/categoria_form.html'
    form_class = CategoriaForm
    success_url = reverse_lazy('inventario:categoria_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nueva Categoría'
        return context


class CategoriaUpdateView(UpdateView):
    model = Categorias
    template_name = 'inventario/categoria_form.html'
    form_class = CategoriaForm
    success_url = reverse_lazy('inventario:categoria_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Categoría'
        return context


class CategoriaDeleteView(DeleteView):
    model = Categorias
    template_name = 'inventario/categoria_confirm_delete.html'
    success_url = reverse_lazy('inventario:categoria_list')


# PROVEEDORES
class ProveedorListView(ListView):
    model = Proveedores
    template_name = 'inventario/proveedor_list.html'
    context_object_name = 'proveedores'
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
                Q(email__icontains=busqueda) |
                Q(telefono__icontains=busqueda)
            )
            
        return queryset.order_by('nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = ['ACTIVO', 'INACTIVO']
        return context


class ProveedorCreateView(CreateView):
    model = Proveedores
    template_name = 'inventario/proveedor_form.html'
    form_class = ProveedorForm 
    success_url = reverse_lazy('inventario:proveedor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Proveedor'
        return context


class ProveedorUpdateView(UpdateView):
    model = Proveedores
    template_name = 'inventario/proveedor_form.html'
    form_class = ProveedorForm 
    success_url = reverse_lazy('inventario:proveedor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Proveedor'
        return context


class ProveedorDeleteView(DeleteView):
    model = Proveedores
    template_name = 'inventario/proveedor_confirm_delete.html'
    success_url = reverse_lazy('inventario:proveedor_list')

class ProveedorDetailView(DetailView):
    model = Proveedores
    template_name = 'inventario/proveedor_detail.html'
    context_object_name = 'proveedor'

# INVENTARIO
class InventarioListView(ListView):
    model = Inventario
    template_name = 'inventario/inventario_list.html'
    context_object_name = 'inventarios'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        
        producto = self.request.GET.get('producto')
        bodega = self.request.GET.get('bodega')
        estado = self.request.GET.get('estado')

        if producto:
            queryset = queryset.filter(producto_id=producto)
        if bodega:
            queryset = queryset.filter(bodega_id=bodega)
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset.order_by('-fecha_registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['productos'] = Producto.objects.all()
        context['bodegas'] = Bodegas.objects.all()
        context['estados'] = ['DISPONIBLE', 'RESERVADO', 'AGOTADO']
        return context


class InventarioCreateView(CreateView):
    model = Inventario
    template_name = 'inventario/inventario_create.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Registro de Inventario'
        context['productos'] = Producto.objects.all()
        context['bodegas'] = Bodegas.objects.all()
        context['proveedores'] = Proveedores.objects.all()
        return context


class InventarioUpdateView(UpdateView):
    model = Inventario
    template_name = 'inventario/inventario_create.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Inventario'
        context['productos'] = Producto.objects.all()
        context['bodegas'] = Bodegas.objects.all()
        context['proveedores'] = Proveedores.objects.all()
        return context


class InventarioDeleteView(DeleteView):
    model = Inventario
    template_name = 'inventario/inventario_confirm_delete.html'
    success_url = reverse_lazy('inventario:inventario_list')

class InventarioDetailView(DetailView):
    model = Inventario
    template_name = 'inventario/inventario_detail.html'
    context_object_name = 'item'  # Para coincidir con el template
    