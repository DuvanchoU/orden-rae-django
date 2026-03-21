from django.utils import timezone
from django.conf import settings
import os
from .models import Producto, Bodegas, Categorias, Proveedores, Inventario

def get_logo_path():
    try:
        # Intenta obtener STATIC_ROOT, si no, usa el primero de STATICFILES_DIRS
        static_root = getattr(settings, 'STATIC_ROOT', None)
        if not static_root and settings.STATICFILES_DIRS:
            static_root = settings.STATICFILES_DIRS[0]
        
        if not static_root:
            return None
            
        logo_path = os.path.join(static_root, 'img', 'Super_Bodega_Logo.PNG')
        
        # Verifica que el archivo exista
        if not os.path.exists(logo_path):
            return None
            
        # Convierte a ruta URI para PDF (file:///C:/...)
        return f'file:///{logo_path.replace("\\", "/")}'
    except Exception as e:
        print(f"Error obteniendo logo: {e}")
        return None

def get_productos_report_data(queryset, request):
    """Genera datos para el reporte de Productos"""
    headers = ['Código', 'Producto', 'Categoría', 'Color', 'Precio', 'Estado']
    rows = []
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

    context = {
        'report_title': 'Reporte de Productos',
        'report_subtitle': 'Catálogo de productos del inventario',
        'headers': headers,
        'rows': rows,
        'generated_at': timezone.now(),
        'logo_path': get_logo_path(),
        'total_records': queryset.count(),
        'productos_disponibles': disponibles,
        'productos_agotados': agotados,
        'filters_applied': _get_productos_filters_summary(request),
    }

    return {
        'headers': headers,
        'rows': rows,
        'context': context,
        'filename': f"productos_{timezone.now().strftime('%Y%m%d')}"
    }

def get_inventario_report_data(queryset, request):
    """Genera datos para el reporte de Inventario"""
    headers = ['Producto', 'Código', 'Bodega', 'Stock Total', 'Disponible', 'Reservado', 'Estado']
    rows = []
    
    total_stock = 0
    total_disponible = 0
    total_reservado = 0
    bodegas_set = set()

    for item in queryset:
        cantidad_reservada = getattr(item, 'cantidad_reservada', 0) or 0
        stock_libre = item.cantidad_disponible - cantidad_reservada
        
        rows.append([
            f"{item.producto.codigo_producto} - {item.producto.referencia_producto or ''}",
            item.producto.codigo_producto,
            item.bodega.nombre_bodega,
            item.cantidad_disponible,
            stock_libre,
            cantidad_reservada,
            item.estado
        ])

        total_stock += item.cantidad_disponible
        total_disponible += stock_libre
        total_reservado += cantidad_reservada
        bodegas_set.add(item.bodega.id_bodega)

    context = {
        'report_title': 'Reporte de Inventario',
        'report_subtitle': 'Control de stock por bodega',
        'headers': headers,
        'rows': rows,
        'generated_at': timezone.now(),
        'total_records': queryset.count(),
        'total_stock': total_stock,
        'total_disponible': total_disponible,
        'total_reservado': total_reservado,
        'bodegas_activas': len(bodegas_set),
        'filters_applied': _get_inventario_filters_summary(request),
    }

    return {
        'headers': headers,
        'rows': rows,
        'context': context,
        'filename': f"inventario_{timezone.now().strftime('%Y%m%d')}"
    }

def get_proveedores_report_data(queryset, request):
    """Genera datos para el reporte de Proveedores"""
    headers = ['ID', 'Nombre', 'Teléfono', 'Email', 'Dirección', 'Estado', 'Fecha Registro']
    rows = []
    
    total_proveedores = 0
    activos_count = 0
    inactivos_count = 0

    for prov in queryset:
        rows.append([
            prov.id_proveedor,
            prov.nombre,
            prov.telefono or '-',
            prov.email or '-',
            prov.direccion or '-',
            prov.estado,
            prov.created_at.strftime('%d/%m/%Y') if prov.created_at else '-'
        ])

        total_proveedores += 1
        if prov.estado == 'ACTIVO':
            activos_count += 1
        else:
            inactivos_count += 1
    
    context = {
        'report_title': 'Reporte de Proveedores',
        'report_subtitle': 'Directorio de contactos y suministros',
        'headers': headers,
        'rows': rows,
        'generated_at': timezone.now(),
        'total_records': total_proveedores,
        'total_proveedores': total_proveedores,
        'proveedores_activos': activos_count,
        'proveedores_inactivos': inactivos_count,
        'filters_applied': _get_proveedores_filters_summary(request),
    }

    return {
        'headers': headers,
        'rows': rows,
        'context': context,
        'filename': f"proveedores_{timezone.now().strftime('%Y%m%d')}"
    }

# --- Helpers de Filtros ---

def _get_productos_filters_summary(request):
    filters = []
    if request.GET.get('busqueda'):
        filters.append(f"Búsqueda: {request.GET['busqueda']}")
    if request.GET.get('categoria'):
        cat = Categorias.objects.filter(id_categorias=request.GET['categoria']).first()
        if cat: filters.append(f"Categoría: {cat.nombre_categoria}")
    if request.GET.get('estado'):
        filters.append(f"Estado: {request.GET['estado']}")
    return ', '.join(filters) if filters else 'Ninguno'

def _get_inventario_filters_summary(request):
    filters = []
    if request.GET.get('producto'):
        prod = Producto.objects.filter(id_producto=request.GET['producto']).first()
        if prod: filters.append(f"Producto: {prod.codigo_producto}")
    if request.GET.get('bodega'):
        bod = Bodegas.objects.filter(id_bodega=request.GET['bodega']).first()
        if bod: filters.append(f"Bodega: {bod.nombre_bodega}")
    if request.GET.get('estado'):
        filters.append(f"Estado: {request.GET['estado']}")
    return ', '.join(filters) if filters else 'Ninguno'

def _get_proveedores_filters_summary(request):
    filters = []
    if request.GET.get('busqueda'):
        filters.append(f"Búsqueda: {request.GET['busqueda']}")
    if request.GET.get('estado'):
        filters.append(f"Estado: {request.GET['estado']}")
    return ', '.join(filters) if filters else 'Ninguno'