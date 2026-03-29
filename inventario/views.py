import uuid
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from .models import Producto, Bodegas, Categorias, Proveedores, Inventario, ImagenesProducto
from .forms import InventarioForm, ProductoForm, BodegaForm, CategoriaForm, ProveedorForm
from .report_services import (
    get_productos_report_data, 
    get_inventario_report_data, 
    get_proveedores_report_data
)
from reports.generators.mixins import ReportMixin
from django.conf import settings

# ------------------------------------------------------------------
# PRODUCTOS
# ------------------------------------------------------------------
class ProductoListView(ReportMixin, ListView):
    model = Producto
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 10

    def get_queryset(self):
        # Solo mostrar productos no eliminados (Soft Delete)
        queryset = Producto.objects.filter(deleted_at__isnull=True)
        categoria = self.request.GET.get('categoria')
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if categoria: queryset = queryset.filter(categoria_id=categoria)
        if estado: queryset = queryset.filter(estado=estado)
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
    
    # Métodos de Reporte (Delegados al servicio)
    def get_report_template(self):
        return 'reports/productos_report.html'
    
    def get_report_data(self):
        return get_productos_report_data(self.get_queryset(), self.request)

    
class ProductoCreateView(CreateView):
    model = Producto
    template_name = 'inventario/producto_form.html'
    form_class = ProductoForm 
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Producto'
        context['modo_edicion'] = False
        context['MEDIA_URL'] = settings.MEDIA_URL # Para mostrar imágenes en el template
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Guardar producto
                producto = form.save()
                
                # Manejar imágenes subidas
                imagenes = self.request.FILES.getlist('imagenes')
                imagen_principal_index = int(self.request.POST.get('imagen_principal_index', 0))
                
                for i, imagen in enumerate(imagenes):
                    # Guardar archivo
                    ruta_relativa = self._guardar_imagen(imagen, producto)
                    
                    # Crear registro en BD
                    ImagenesProducto.objects.create(
                        producto=producto,
                        ruta_imagen=ruta_relativa,
                        descripcion=f"Imagen {i+1} de {producto.codigo_producto}",
                        es_principal=1 if i == imagen_principal_index else 0
                    )
                
            messages.success(self.request, f'Producto "{producto.codigo_producto}" creado exitosamente.')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al crear: {str(e)}')
            return super().form_invalid(form)
    
    def _guardar_imagen(self, imagen, producto):
        """Guarda la imagen y retorna la ruta relativa"""
        # Crear ruta: productos/[codigo_producto]/[nombre_archivo]
        carpeta = os.path.join(settings.MEDIA_ROOT, 'productos', producto.codigo_producto)
        os.makedirs(carpeta, exist_ok=True)
        
        extension = os.path.splitext(imagen.name)[1]
        nombre_archivo = f"{producto.codigo_producto}_{uuid.uuid4().hex}{extension}"
        ruta_completa = os.path.join(carpeta, nombre_archivo)
        
        # Guardar archivo
        with open(ruta_completa, 'wb+') as destination:
            for chunk in imagen.chunks():
                destination.write(chunk)
        
        # Retornar ruta relativa para BD
        return os.path.join('productos', producto.codigo_producto, nombre_archivo)
    

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
        context['modo_edicion'] = True
        context['MEDIA_URL'] = settings.MEDIA_URL # Para mostrar imágenes en el template
        
        # Obtener imágenes existentes
        context['imagenes_existentes'] = ImagenesProducto.objects.filter(
            producto=self.object
        ).order_by('-es_principal', '-created_at')
        
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                producto = form.save()
                
                # Obtener imágenes a eliminar (marcadas en el formulario)
                imagenes_a_eliminar = self.request.POST.getlist('imagenes_a_eliminar')
                
                # Filtrar valores vacíos
                imagenes_a_eliminar = [id for id in imagenes_a_eliminar if id]
                
                # Eliminar imágenes marcadas
                for id_imagen in imagenes_a_eliminar:
                    try:
                        img = ImagenesProducto.objects.get(id_imagen=id_imagen, producto=producto)
                        # Eliminar archivo físico
                        if img.ruta_imagen and os.path.exists(os.path.join(settings.MEDIA_ROOT, img.ruta_imagen)):
                            os.remove(os.path.join(settings.MEDIA_ROOT, img.ruta_imagen))
                        img.delete()
                    except ImagenesProducto.DoesNotExist:
                        pass
                
                # Agregar nuevas imágenes
                nuevas_imagenes = self.request.FILES.getlist('nuevas_imagenes')
                
                for i, imagen in enumerate(nuevas_imagenes):
                    ruta_relativa = self._guardar_imagen(imagen, producto)
                    
                    # Determinar si es principal (si no hay imágenes principales existentes)
                    hay_principal = ImagenesProducto.objects.filter(
                        producto=producto, 
                        es_principal=1
                    ).exists()
                    
                    ImagenesProducto.objects.create(
                        producto=producto,
                        ruta_imagen=ruta_relativa,
                        descripcion=f"Imagen {i+1} de {producto.codigo_producto}",
                        es_principal=0 if hay_principal else 1
                    )
                
            messages.success(self.request, f'Producto "{producto.codigo_producto}" actualizado correctamente.')
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return super().form_invalid(form)
    
    def _guardar_imagen(self, imagen, producto):
        """Guarda la imagen y retorna la ruta relativa"""
        carpeta = os.path.join(settings.MEDIA_ROOT, 'productos', producto.codigo_producto)
        os.makedirs(carpeta, exist_ok=True)
        
        nombre_archivo = f"{producto.codigo_producto}_{imagen.name}"
        ruta_completa = os.path.join(carpeta, nombre_archivo)
        
        with open(ruta_completa, 'wb+') as destination:
            for chunk in imagen.chunks():
                destination.write(chunk)
        
        return os.path.join('productos', producto.codigo_producto, nombre_archivo)

# ------------------------------------------------------------------
# ELIMINAR PRODUCTO (SOFT DELETE) 
# ------------------------------------------------------------------
class ProductoDeleteView(View):
    
    # 1. Método GET: Muestra la página de confirmación
    def get(self, request, pk):
        # Obtenemos el producto para mostrar sus datos en la plantilla
        producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
        return render(request, 'inventario/producto_confirm_delete.html', {'object': producto})

    # 2. Método POST: Ejecuta el borrado lógico (Soft Delete)
    def post(self, request, pk):
        try:
            producto = get_object_or_404(Producto, pk=pk, deleted_at__isnull=True)
            producto.soft_delete() # Usa el método del modelo que ya creamos
            messages.success(request, f'Producto "{producto.codigo_producto}" eliminado correctamente (Oculto).')
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
        context['MEDIA_URL'] = settings.MEDIA_URL # Para mostrar imágenes en el template
        
        # Obtener todas las imágenes del producto
        from .models import ImagenesProducto
        imagenes = ImagenesProducto.objects.filter(
            producto=self.object
        ).order_by('-es_principal', '-created_at')
        
        context['imagenes'] = imagenes
        context['imagen_principal'] = imagenes.first() if imagenes.exists() else None

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
# BODEGAS 
# ------------------------------------------------------------------
class BodegaListView(ListView):
    model = Bodegas
    template_name = 'inventario/bodega_list.html'
    context_object_name = 'bodegas'
    paginate_by = 10

    def get_queryset(self):
        # Solo mostrar bodegas no eliminadas (Soft Delete)
        queryset = Bodegas.objects.filter(deleted_at__isnull=True)
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
        # Guardar timestamps automáticamente
        form.instance.created_at = timezone.now()
        form.instance.updated_at = timezone.now()
        messages.success(self.request, 'Bodega creada exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al crear la bodega. Verifica los datos.')
        return super().form_invalid(form)
    

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
        # Actualizar timestamp
        form.instance.updated_at = timezone.now()
        messages.success(self.request, 'Bodega actualizada correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar la bodega. Verifica los datos.')
        return super().form_invalid(form)
    

class BodegaDeleteView(DeleteView):
    model = Bodegas
    template_name = 'inventario/bodega_confirm_delete.html'
    success_url = reverse_lazy('inventario:bodega_list')

    def delete(self, request, *args, **kwargs):
        # SOFT DELETE: En lugar de eliminar, marcar deleted_at
        obj = self.get_object()
        obj.deleted_at = timezone.now()
        obj.save()
        messages.success(self.request, 'Bodega desactivada correctamente.')
        return redirect(self.success_url)

# ------------------------------------------------------------------
# CATEGORÍAS
# ------------------------------------------------------------------
class CategoriaListView(ListView):
    model = Categorias
    template_name = 'inventario/categoria_list.html'
    context_object_name = 'categorias'
    paginate_by = 15
    
    def get_queryset(self):
        # Solo mostrar categorías, no eliminadas (Soft Delete)
        queryset = Categorias.objects.filter(deleted_at__isnull=True)
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
        # Guardar timestamps automáticamente
        form.instance.created_at = timezone.now()
        form.instance.updated_at = timezone.now()
        messages.success(self.request, 'Categoría creada exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al crear la categoría. Verifica los datos.')
        return super().form_invalid(form)


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
        # Actualizar timestamp
        form.instance.updated_at = timezone.now()
        messages.success(self.request, 'Categoría actualizada correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar la categoría. Verifica los datos.')
        return super().form_invalid(form)
    

class CategoriaDeleteView(DeleteView):
    model = Categorias
    template_name = 'inventario/categoria_confirm_delete.html'
    success_url = reverse_lazy('inventario:categoria_list')

    def delete(self, request, *args, **kwargs):
        # SOFT DELETE: En lugar de eliminar, marcar deleted_at
        obj = self.get_object()
        obj.deleted_at = timezone.now()
        obj.save()
        messages.success(self.request, 'Categoría desactivada correctamente.')
        return redirect(self.success_url)

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    
# ------------------------------------------------------------------
# PROVEEDORES
# ------------------------------------------------------------------
class ProveedorListView(ReportMixin, ListView):
    model = Proveedores
    template_name = 'inventario/proveedor_list.html'
    context_object_name = 'proveedores'
    paginate_by = 10

    def get_queryset(self):
        # Solo mostrar proveedores no eliminados (Soft Delete)
        queryset = Proveedores.objects.filter(deleted_at__isnull=True)
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')
        if estado: queryset = queryset.filter(estado=estado)
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
    
    # Métodos de Reporte (Delegados al servicio)
    def get_report_template(self):
        return 'reports/proveedores_report.html'
    
    def get_report_data(self):
        return get_proveedores_report_data(self.get_queryset(), self.request)

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
        # Guardar timestamps automáticamente
        form.instance.created_at = timezone.now()
        form.instance.updated_at = timezone.now()
        messages.success(self.request, f'Proveedor "{form.instance.nombre}" registrado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al registrar el proveedor. Verifica los datos.')
        return super().form_invalid(form)
    

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
        # Actualizar timestamp
        form.instance.updated_at = timezone.now()
        messages.success(self.request, f'Proveedor "{form.instance.nombre}" actualizado correctamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar el proveedor. Verifica los datos.')
        return super().form_invalid(form)
    

class ProveedorDeleteView(DeleteView):
    model = Proveedores
    template_name = 'inventario/proveedor_confirm_delete.html'
    success_url = reverse_lazy('inventario:proveedor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si tiene pedidos/compras asociados
        context['tiene_pedidos'] = self.object.tiene_pedidos_asociados()
        context['cantidad_pedidos'] = self.object.compras_set.filter(deleted_at__isnull=True).count() if hasattr(self.object, 'compras_set') else 0
        return context
    
    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        
        # VALIDACIÓN: No eliminar si tiene pedidos asociados
        if obj.tiene_pedidos_asociados():
            messages.error(
                self.request, 
                f'No se puede eliminar el proveedor "{obj.nombre}" porque tiene pedidos asociados.'
            )
            return redirect(self.success_url)
        
        # SOFT DELETE: Marcar deleted_at
        obj.deleted_at = timezone.now()
        obj.save()
        
        messages.success(self.request, f'Proveedor "{obj.nombre}" desactivado correctamente.')
        return redirect(self.success_url)
    
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
    

class ProveedorDetailView(DetailView):
    model = Proveedores
    template_name = 'inventario/proveedor_detail.html'
    context_object_name = 'proveedor'

    def get_queryset(self):
        # Solo mostrar proveedores no eliminados
        return Proveedores.objects.filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar información adicional
        proveedor = self.get_object()
        
        # Contar pedidos/compras asociadas
        if hasattr(proveedor, 'compras_set'):
            context['total_compras'] = proveedor.compras_set.filter(deleted_at__isnull=True).count()
        else:
            context['total_compras'] = 0
        
        return context

# ------------------------------------------------------------------
# LISTA DE INVENTARIO
# ------------------------------------------------------------------
class InventarioListView(ReportMixin, ListView):
    model = Inventario
    template_name = 'inventario/inventario_list.html'
    context_object_name = 'inventarios'
    paginate_by = 10

    def get_queryset(self):
        # 1. Filtrar solo registros activos (Soft Delete)
        # 2. Usar select_related para optimizar consultas SQL (trae producto, bodega y proveedor de una vez)
        queryset = Inventario.objects.filter(
            deleted_at__isnull=True
        ).select_related('producto', 'bodega', 'proveedor')

        # Obtener parámetros de filtro
        producto = self.request.GET.get('producto')
        bodega = self.request.GET.get('bodega')
        estado = self.request.GET.get('estado')

        # Aplicar filtros dinámicos
        if producto: queryset = queryset.filter(producto_id=producto)
        if bodega: queryset = queryset.filter(bodega_id=bodega)
        if estado: queryset = queryset.filter(estado=estado)

        # Ordenar por fecha de registro (más reciente primero)  
        return queryset.order_by('-fecha_registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['productos'] = Producto.objects.filter(deleted_at__isnull=True)
        context['bodegas'] = Bodegas.objects.all()
        context['estados'] = ['DISPONIBLE', 'COMPROMETIDO', 'AGOTADO']
        context['titulo'] = 'Inventario'

        # Calcular stock libre para cada item
        inventarios_con_calculo = []
        for inv in context['inventarios']:
            # Forzamos los valores a entero (si son None, usamos 0)
            total = inv.cantidad_disponible or 0
            reservado = inv.cantidad_reservada or 0
            libre = total - reservado

            # Guardamos el objeto original pero le añadimos un atributo extra 'stock_libre'
            inv.stock_libre = libre 
            inventarios_con_calculo.append(inv)
            
        # Sobrescribimos la lista de inventarios con la nueva que tiene el cálculo
        context['inventarios'] = inventarios_con_calculo

        return context

    # Métodos de Reporte (Delegados al servicio)
    def get_report_template(self):
        return 'reports/inventario_report.html'
    
    def get_report_data(self):
        return get_inventario_report_data(self.get_queryset(), self.request)
    
# ------------------------------------------------------------------
# CREAR REGISTRO
# ------------------------------------------------------------------
class InventarioCreateView(CreateView):
    model = Inventario
    template_name = 'inventario/inventario_form.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Registro de Inventario'
        return context
    
    def form_valid(self, form):
        # Mensaje personalizado con el código del producto
        messages.success(self.request, 
                         f"Inventario creado exitosamente para '{form.instance.producto.codigo_producto}' en '{form.instance.bodega.nombre_bodega}'."
        )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Error al crear. Verifique que no exista un registro duplicado para este producto y bodega.")
        return super().form_invalid(form)

# ------------------------------------------------------------------
# EDITAR REGISTRO
# ------------------------------------------------------------------
class InventarioUpdateView(UpdateView):
    model = Inventario
    template_name = 'inventario/inventario_form.html'
    form_class = InventarioForm
    success_url = reverse_lazy('inventario:inventario_list')

    def get_queryset(self):
        # Solo permitir editar registros que NO estén eliminados
        return Inventario.objects.filter(deleted_at__isnull=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Inventario'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Registro de inventario actualizado correctamente.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error al actualizar. Revise los datos ingresados.")
        return super().form_invalid(form)
    
# ------------------------------------------------------------------
# ELIMINAR REGISTRO (SOFT DELETE) 
# ------------------------------------------------------------------
class InventarioDeleteView(View):
    
    # 1. Método GET: Muestra la página de confirmación
    def get(self, request, pk):
        item = get_object_or_404(Inventario, pk=pk, deleted_at__isnull=True)
        return render(request, 'inventario/inventario_confirm_delete.html', {'item': item})

    # 2. Método POST: Ejecuta el borrado real
    def post(self, request, pk):
        try:
            item = get_object_or_404(Inventario, pk=pk, deleted_at__isnull=True)
            item.deleted_at = timezone.now()
            item.save()
            messages.success(request, "Registro eliminado correctamente (Oculto).")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
        return redirect('inventario:inventario_list')

# ------------------------------------------------------------------
# DETALLE DEL REGISTRO
# ------------------------------------------------------------------
class InventarioDetailView(DetailView):
    model = Inventario
    template_name = 'inventario/inventario_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        # Solo mostrar detalles de registros activos
        # select_related es crucial aquí para no hacer consultas extra al acceder a producto/bodega/proveedor
        return Inventario.objects.filter(
            deleted_at__isnull=True
        ).select_related('producto', 'bodega', 'proveedor')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el objeto actual
        item = self.object
        
        # --- CÁLCULO DE STOCK SEGURO EN PYTHON ---
        # Usamos 'or 0' para asegurar que si viene None, se trate como 0
        total = item.cantidad_disponible or 0
        reservado = item.cantidad_reservada or 0
        
        # Calculamos el libre
        stock_libre = total - reservado
        
        # Inyectamos las variables calculadas al contexto del template
        context['stock_libre'] = stock_libre
        context['total_fisico'] = total
        context['cantidad_reservada'] = reservado
        
        return context