from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from .models import Producto, Bodegas, Categorias, Proveedores, Inventario
from .forms import InventarioForm, ProductoForm, BodegaForm, CategoriaForm, ProveedorForm
from reports.generators.mixins import ReportMixin
from django.conf import settings
import os

# ------------------------------------------------------------------
# PRODUCTOS
# ------------------------------------------------------------------
class ProductoListView(ReportMixin, ListView):
    model = Producto
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 10

    def get_queryset(self):
        # FILTRO CRÍTICO: Solo mostrar productos no eliminados (Soft Delete)
        queryset = Producto.objects.filter(deleted_at__isnull=True)
        
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

        # ORDENAMIENTO: Primero por Código (A-Z)
        return queryset.order_by('codigo_producto','-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categorias.objects.all()
        context['estados'] = ['DISPONIBLE', 'AGOTADO']
        context['titulo'] = 'Listado de Productos'
        return context

    # ============================================
    # MÉTODOS PARA REPORTES (ReportMixin)
    # ============================================
    def get(self, request, *args, **kwargs):
        # Verificar si se solicita un reporte
        report_format = request.GET.get('format')
        if report_format:
            return self.render_report(report_format)
        return super().get(request, *args, **kwargs)
    
    def get_report_template(self):
        """Template específico para reporte de productos"""
        return 'reports/productos_report.html'
    
    def get_report_data(self):
        """Prepara los datos para el reporte"""
        queryset = self.get_queryset()
        
        # Headers y rows para Excel/CSV
        headers = ['Código', 'Producto', 'Categoría', 'Color', 'Precio', 'Estado']
        rows = []
        
        # Contadores para el resumen
        disponibles = 0
        agotados = 0

        for producto in queryset:
            rows.append([
                producto.codigo_producto,
                f"{producto.referencia_producto or 'Sin referencia'}",
                producto.categoria.nombre_categoria,
                producto.color_producto or '-',
                f"${producto.precio_actual:,.0f}".replace(',', '.'),
                producto.estado
            ])
            
            if producto.estado == 'DISPONIBLE':
                disponibles += 1
            else:
                agotados += 1
                
        logo_path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'img/Super_Bodega_Logo.PNG')
        logo_path = f'file:///{logo_path.replace("\\", "/")}'

        # Contexto para PDF (HTML)
        context = {
            'report_title': 'Reporte de Productos',
            'report_subtitle': 'Catálogo de productos del inventario',
            'headers': headers,
            'rows': rows,
            'generated_at': timezone.now(),
            'logo_path': logo_path,
            'total_records': queryset.count(),
            'productos_disponibles': disponibles,
            'productos_agotados': agotados,
            'filters_applied': self._get_filters_summary(),
        }
        
        return {
            'headers': headers,
            'rows': rows,
            'context': context,
            'filename': f"productos_{timezone.now().strftime('%Y%m%d')}"
        }
    
    def _get_filters_summary(self):
        """Resume los filtros aplicados para el reporte"""
        filters = []
        if self.request.GET.get('busqueda'):
            filters.append(f"Búsqueda: {self.request.GET['busqueda']}")
        if self.request.GET.get('categoria'):
            cat = Categorias.objects.filter(id_categorias=self.request.GET['categoria']).first()
            if cat:
                filters.append(f"Categoría: {cat.nombre_categoria}")
        if self.request.GET.get('estado'):
            filters.append(f"Estado: {self.request.GET['estado']}")
        return ', '.join(filters) if filters else 'Ninguno'
    
class ProductoCreateView(CreateView):
    model = Producto
    template_name = 'inventario/producto_form.html'
    form_class = ProductoForm 
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Producto'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Producto creado exitosamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error al crear el producto. Verifique los datos.')
        return super().form_invalid(form)

class ProductoUpdateView(UpdateView):
    model = Producto
    template_name = 'inventario/producto_form.html'
    form_class = ProductoForm 
    success_url = reverse_lazy('inventario:producto_list')

    def get_queryset(self):
        # No permitir editar productos eliminados
        return Producto.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Producto'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Producto actualizado correctamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar. Revise los campos.')
        return super().form_invalid(form)

# Vista personalizada para Soft Delete
class ProductoDeleteView(View):
    def post(self, request, pk):
        try:
            producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
            producto.soft_delete() # Usa el método del modelo
            messages.success(request, f'Producto "{producto.codigo_producto}" eliminado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {str(e)}')
        return redirect('inventario:producto_list')

class ProductoDetailView(DetailView):
    model = Producto
    template_name = 'inventario/producto_detail.html'
    context_object_name = 'producto'

    def get_queryset(self):
        return Producto.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lógica para obtener el nombre del proveedor manualmente
        producto = self.object
        if producto.proveedor_id:
            try:
                proveedor_obj = Proveedores.objects.get(id_proveedor=producto.proveedor_id)
                context['nombre_proveedor'] = proveedor_obj.nombre
                context['estado_proveedor'] = proveedor_obj.estado
            except Proveedores.DoesNotExist:
                context['nombre_proveedor'] = None
        else:
            context['nombre_proveedor'] = None
            
        return context
    
# ------------------------------------------------------------------
# BODEGAS (Patrón similar aplicado a todos)
# ------------------------------------------------------------------
class BodegaListView(ListView):
    model = Bodegas
    template_name = 'inventario/bodega_list.html'
    context_object_name = 'bodegas'
    paginate_by = 10
    # Nota: Si usas soft delete en Bodegas, agrega .filter(deleted_at__isnull=True) aquí

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
        context['titulo'] = 'Bodegas'
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
    def form_valid(self, form):
        messages.success(self.request, 'Bodega creada exitosamente.')
        return super().form_valid(form)

class BodegaUpdateView(UpdateView):
    model = Bodegas
    template_name = 'inventario/bodega_form.html'
    form_class = BodegaForm
    success_url = reverse_lazy('inventario:bodega_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Bodega'
        return context
    def form_valid(self, form):
        messages.success(self.request, 'Bodega actualizada correctamente.')
        return super().form_valid(form)

class BodegaDeleteView(DeleteView):
    model = Bodegas
    template_name = 'inventario/bodega_confirm_delete.html'
    success_url = reverse_lazy('inventario:bodega_list')
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Bodega eliminada correctamente.')
        return super().delete(request, *args, **kwargs)

# ------------------------------------------------------------------
# CATEGORÍAS
# ------------------------------------------------------------------
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
        context['titulo'] = 'Categorías'
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
    def form_valid(self, form):
        messages.success(self.request, 'Categoría creada exitosamente.')
        return super().form_valid(form)

class CategoriaUpdateView(UpdateView):
    model = Categorias
    template_name = 'inventario/categoria_form.html'
    form_class = CategoriaForm
    success_url = reverse_lazy('inventario:categoria_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Categoría'
        return context
    def form_valid(self, form):
        messages.success(self.request, 'Categoría actualizada correctamente.')
        return super().form_valid(form)

class CategoriaDeleteView(DeleteView):
    model = Categorias
    template_name = 'inventario/categoria_confirm_delete.html'
    success_url = reverse_lazy('inventario:categoria_list')
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Categoría eliminada correctamente.')
        return super().delete(request, *args, **kwargs)

# ------------------------------------------------------------------
# PROVEEDORES
# ------------------------------------------------------------------
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
        context['titulo'] = 'Proveedores'
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
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor registrado exitosamente.')
        return super().form_valid(form)

class ProveedorUpdateView(UpdateView):
    model = Proveedores
    template_name = 'inventario/proveedor_form.html'
    form_class = ProveedorForm 
    success_url = reverse_lazy('inventario:proveedor_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Proveedor'
        return context
    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado correctamente.')
        return super().form_valid(form)

class ProveedorDeleteView(DeleteView):
    model = Proveedores
    template_name = 'inventario/proveedor_confirm_delete.html'
    success_url = reverse_lazy('inventario:proveedor_list')
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Proveedor eliminado correctamente.')
        return super().delete(request, *args, **kwargs)

class ProveedorDetailView(DetailView):
    model = Proveedores
    template_name = 'inventario/proveedor_detail.html'
    context_object_name = 'proveedor'

# ------------------------------------------------------------------
# INVENTARIO
# ------------------------------------------------------------------
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
        context['productos'] = Producto.objects.filter(deleted_at__isnull=True)
        context['bodegas'] = Bodegas.objects.all()
        context['estados'] = ['DISPONIBLE', 'RESERVADO', 'AGOTADO']
        context['titulo'] = 'Inventario'
        return context

class InventarioCreateView(CreateView):
    model = Inventario
    template_name = 'inventario/inventario_create.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Registro de Inventario'
        return context
    def form_valid(self, form):
        messages.success(self.request, 'Registro de inventario creado.')
        return super().form_valid(form)

class InventarioUpdateView(UpdateView):
    model = Inventario
    template_name = 'inventario/inventario_create.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Inventario'
        return context
    def form_valid(self, form):
        messages.success(self.request, 'Inventario actualizado.')
        return super().form_valid(form)

class InventarioDeleteView(DeleteView):
    model = Inventario
    template_name = 'inventario/inventario_confirm_delete.html'
    success_url = reverse_lazy('inventario:inventario_list')
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Registro eliminado.')
        return super().delete(request, *args, **kwargs)

class InventarioDetailView(DetailView):
    model = Inventario
    template_name = 'inventario/inventario_detail.html'
    context_object_name = 'item'