# dashboard/views.py
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth import logout as django_logout
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

# Importación de modelos de otras apps
from produccion.models import Produccion
from ventas.models import Pedido, Ventas, Cotizaciones, Clientes
from inventario.models import Producto, Inventario, Categorias, Proveedores
from compras.models import Compras
from usuarios.models import Usuarios

# Importación de decoradores personalizados
from usuarios.decorators import login_required_custom, role_required


# =============================================================================
# === REDIRECCIÓN DE DASHBOARD SEGÚN ROL ===
# =============================================================================
@login_required_custom
def dashboard_redirect(request):
    """
    Redirige al usuario al dashboard correspondiente según su rol.
    Esta es la vista principal que se llama al acceder a /dashboard/
    """
    # Verificar que el usuario tenga un rol asignado
    if not hasattr(request.user, 'id_rol') or not request.user.id_rol:
        return redirect('usuarios:login')
    
    rol = request.user.id_rol.nombre_rol
    
    # Mapa de redirección por rol
    rol_dashboard_map = {
        'GERENTE': 'dashboard:dashboard_gerente',
        'ASESOR COMERCIAL': 'dashboard:dashboard_asesor',
        'JEFE LOGISTICO': 'dashboard:dashboard_logistica',
        'AUXILIAR DE BODEGA': 'dashboard:dashboard_bodega',
        'CLIENTE': 'pagina:index'  # Los clientes van al home público
    }
    
    # Obtener la URL del dashboard correspondiente o redirigir al de gerente por defecto
    dashboard_name = rol_dashboard_map.get(rol, 'dashboard:dashboard_gerente')
    return redirect(dashboard_name)


# =============================================================================
# === DASHBOARD GERENTE (ACCESO COMPLETO) ===
# =============================================================================
class DashboardView(TemplateView):
    """
    Vista principal del dashboard - Solo accesible para GERENTE.
    Muestra todas las estadísticas y métricas del sistema ERP.
    """
    template_name = 'dashboard/gerente.html'
    
    @method_decorator(role_required(['GERENTE']))
    def dispatch(self, *args, **kwargs):
        """Verifica permisos antes de ejecutar cualquier método HTTP"""
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # === CONTADORES TOTALES ===
        context['total_produccion'] = Produccion.objects.count()
        context['total_pedidos'] = Pedido.objects.count()
        context['total_ventas'] = Ventas.objects.count()
        context['total_productos'] = Producto.objects.count()
        context['total_cotizaciones'] = Cotizaciones.objects.count()
        context['total_compras'] = Compras.objects.count()
        context['total_usuarios'] = Usuarios.objects.count()
        
        # === VENTAS DEL MES ===
        hoy = timezone.now()
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ventas_mes_qs = Ventas.objects.filter(fecha_venta__gte=inicio_mes)
        context['ventas_mes'] = ventas_mes_qs.count()
        context['ingresos_mes'] = ventas_mes_qs.aggregate(total=Sum('total'))['total'] or 0
        
        # === PEDIDOS POR ESTADO ===
        context['pedidos_pendientes'] = Pedido.objects.filter(estado_pedido='PENDIENTE').count()
        context['pedidos_proceso'] = Pedido.objects.filter(estado_pedido='EN PROCESO').count()
        context['pedidos_completados'] = Pedido.objects.filter(estado_pedido='COMPLETADO').count()
        
        # === PRODUCCIÓN POR ESTADO ===
        context['produccion_pendiente'] = Produccion.objects.filter(estado_produccion='PENDIENTE').count()
        context['produccion_proceso'] = Produccion.objects.filter(estado_produccion='EN PROCESO').count()
        context['produccion_terminada'] = Produccion.objects.filter(estado_produccion='TERMINADA').count()
        
        # === INVENTARIO ===
        context['productos_bajo_stock'] = Inventario.objects.filter(cantidad_disponible__lte=5).count()
        context['productos_sin_stock'] = Inventario.objects.filter(cantidad_disponible=0).count()
        
        # === COTIZACIONES POR ESTADO ===
        context['cotizaciones_pendientes'] = Cotizaciones.objects.filter(estado='borrador').count()
        context['cotizaciones_enviadas'] = Cotizaciones.objects.filter(estado='enviada').count()
        context['cotizaciones_aceptadas'] = Cotizaciones.objects.filter(estado='aceptada').count()
        
        # === ÚLTIMAS VENTAS (con relación a cliente) ===
        context['ultimas_ventas'] = Ventas.objects.select_related('cliente').order_by('-fecha_venta')[:5]
        
        # === ÚLTIMOS PEDIDOS (con relación a cliente) ===
        context['ultimos_pedidos'] = Pedido.objects.select_related('cliente').order_by('-fecha_pedido')[:5]
        
        # === DATOS PARA GRÁFICAS ===
        context['ventas_6_meses'] = self._get_ventas_por_mes()
        context['productos_por_categoria'] = self._get_productos_por_categoria()
        context['pedidos_estado_data'] = self._get_pedidos_por_estado()
        
        # === INFORMACIÓN DEL USUARIO ACTUAL ===
        # ✅ CORREGIDO: usa self.request en lugar de request
        if hasattr(self.request, 'user') and hasattr(self.request.user, 'id_rol') and self.request.user.id_rol:
            context['user_rol'] = self.request.user.id_rol.nombre_rol
            context['user_nombre'] = f"{self.request.user.nombres} {self.request.user.apellidos}"
        else:
            context['user_rol'] = None
            context['user_nombre'] = 'Usuario'
        
        return context
    
    def _get_ventas_por_mes(self):
        """Obtiene datos de ventas de los últimos 6 meses para gráficas"""
        hoy = timezone.now()
        datos = []
        etiquetas = []
        
        for i in range(5, -1, -1):
            mes_ref = hoy - timedelta(days=30*i)
            inicio_mes = mes_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes = inicio_mes + timedelta(days=32)
            fin_mes = fin_mes.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            total = Ventas.objects.filter(
                fecha_venta__gte=inicio_mes,
                fecha_venta__lt=fin_mes
            ).aggregate(total=Sum('total'))['total'] or 0
            
            etiquetas.append(mes_ref.strftime('%b'))
            datos.append(float(total))
        
        return {'etiquetas': etiquetas, 'datos': datos}
    
    def _get_productos_por_categoria(self):
        """Obtiene productos agrupados por categoría para gráfica doughnut"""
        categorias = Categorias.objects.annotate(
            total_productos=Count('productos')
        ).order_by('-total_productos')[:5]
        
        return {
            'etiquetas': [cat.nombre_categoria for cat in categorias],
            'datos': [cat.total_productos for cat in categorias]
        }
    
    def _get_pedidos_por_estado(self):
        """Obtiene pedidos agrupados por estado para gráfica de barras"""
        estados = ['PENDIENTE', 'CONFIRMADO', 'EN PROCESO', 'COMPLETADO', 'CANCELADO']
        datos = []
        
        for estado in estados:
            count = Pedido.objects.filter(estado_pedido=estado).count()
            datos.append(count)
        
        return {'etiquetas': estados, 'datos': datos}


# =============================================================================
# === DASHBOARD ASESOR COMERCIAL ===
# =============================================================================
@role_required(['GERENTE', 'ASESOR COMERCIAL'])
def dashboard_asesor(request):
    """
    Dashboard para Asesor Comercial.
    Enfocado en ventas, pedidos, cotizaciones y gestión de clientes.
    """
    hoy = timezone.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Filtrar ventas del mes actual
    ventas_mes_qs = Ventas.objects.filter(fecha_venta__gte=inicio_mes)
    
    context = {
        # Información del usuario
        'titulo': 'Dashboard Comercial',
        'rol': request.user.id_rol.nombre_rol if hasattr(request.user, 'id_rol') else '',
        'user_nombre': f"{request.user.nombres} {request.user.apellidos}" if hasattr(request.user, 'nombres') else 'Usuario',
        
        # Métricas principales de ventas
        'total_ventas': Ventas.objects.count(),
        'ventas_mes': ventas_mes_qs.count(),
        'ingresos_mes': ventas_mes_qs.aggregate(total=Sum('total'))['total'] or 0,
        
        # Métricas de pedidos
        'total_pedidos': Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado_pedido='PENDIENTE').count(),
        'pedidos_completados': Pedido.objects.filter(estado_pedido='COMPLETADO').count(),
        
        # Métricas de cotizaciones
        'total_cotizaciones': Cotizaciones.objects.count(),
        'cotizaciones_pendientes': Cotizaciones.objects.filter(estado='borrador').count(),
        'cotizaciones_aceptadas': Cotizaciones.objects.filter(estado='aceptada').count(),
        
        # Productos y compras (solo lectura para asesor)
        'total_productos': Producto.objects.count(),
        'total_compras': Compras.objects.count(),
        
        # Listados recientes
        'ultimas_ventas': Ventas.objects.select_related('cliente').order_by('-fecha_venta')[:5],
        'ultimos_pedidos': Pedido.objects.select_related('cliente').order_by('-fecha_pedido')[:5],
        
        # Datos para gráficas (reutilizando métodos de DashboardView)
        'ventas_6_meses': DashboardView()._get_ventas_por_mes(),
        'pedidos_estado_data': DashboardView()._get_pedidos_por_estado(),
    }
    
    return render(request, 'dashboard/asesor.html', context)


# =============================================================================
# === DASHBOARD LOGÍSTICA (JEFE LOGÍSTICO) ===
# =============================================================================
@role_required(['GERENTE', 'JEFE LOGISTICO'])
def dashboard_logistica(request):
    """
    Dashboard para Jefe Logístico.
    Enfocado en inventario, producción, proveedores y gestión de pedidos.
    """
    # Obtener lista de productos con stock bajo para mostrar en tabla
    productos_bajo_stock_lista = Inventario.objects.filter(
        cantidad_disponible__lte=5
    ).select_related('producto', 'producto__categoria')[:5]
    
    # Obtener producción reciente
    produccion_reciente = Produccion.objects.select_related('producto').order_by('-fecha_inicio')[:5]
    
    context = {
        # Información del usuario
        'titulo': 'Dashboard Logística',
        'rol': request.user.id_rol.nombre_rol if hasattr(request.user, 'id_rol') else '',
        'user_nombre': f"{request.user.nombres} {request.user.apellidos}" if hasattr(request.user, 'nombres') else 'Usuario',
        
        # Métricas de inventario
        'total_productos': Producto.objects.count(),
        'productos_bajo_stock': Inventario.objects.filter(cantidad_disponible__lte=5).count(),
        'productos_sin_stock': Inventario.objects.filter(cantidad_disponible=0).count(),
        
        # Métricas de producción
        'total_produccion': Produccion.objects.count(),
        'produccion_pendiente': Produccion.objects.filter(estado_produccion='PENDIENTE').count(),
        'produccion_proceso': Produccion.objects.filter(estado_produccion='EN PROCESO').count(),
        'produccion_terminada': Produccion.objects.filter(estado_produccion='TERMINADA').count(),
        
        # Métricas de pedidos
        'total_pedidos': Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado_pedido='PENDIENTE').count(),
        'pedidos_proceso': Pedido.objects.filter(estado_pedido='EN PROCESO').count(),
        'pedidos_completados': Pedido.objects.filter(estado_pedido='COMPLETADO').count(),
        
        # Compras y proveedores
        'total_compras': Compras.objects.count(),
        
        # Listados para tablas
        'ultimos_pedidos': Pedido.objects.select_related('cliente').order_by('-fecha_pedido')[:5],
        'produccion_reciente': produccion_reciente,
        'productos_bajo_stock_lista': productos_bajo_stock_lista,
        
        # Datos para gráficas
        'productos_por_categoria': DashboardView()._get_productos_por_categoria(),
        'pedidos_estado_data': DashboardView()._get_pedidos_por_estado(),
    }
    
    return render(request, 'dashboard/logistica.html', context)


# =============================================================================
# === DASHBOARD BODEGA (AUXILIAR DE BODEGA) ===
# =============================================================================
@role_required(['GERENTE', 'AUXILIAR DE BODEGA'])
def dashboard_bodega(request):
    """
    Dashboard para Auxiliar de Bodega.
    Vista simplificada enfocada exclusivamente en control de stock y movimientos.
    """
    # Listas críticas para bodega
    productos_bajo_stock_lista = Inventario.objects.filter(
        cantidad_disponible__lte=5,
        cantidad_disponible__gt=0
    ).select_related('producto')[:10]
    
    productos_sin_stock_lista = Inventario.objects.filter(
        cantidad_disponible=0
    ).select_related('producto')[:10]
    
    produccion_reciente = Produccion.objects.filter(
        estado_produccion='EN PROCESO'
    ).select_related('producto').order_by('-fecha_inicio')[:5]
    
    context = {
        # Información del usuario
        'titulo': 'Dashboard Bodega',
        'rol': request.user.id_rol.nombre_rol if hasattr(request.user, 'id_rol') else '',
        'user_nombre': f"{request.user.nombres} {request.user.apellidos}" if hasattr(request.user, 'nombres') else 'Usuario',
        
        # Contadores principales de stock
        'total_productos': Producto.objects.count(),
        'productos_bajo_stock': Inventario.objects.filter(cantidad_disponible__lte=5).count(),
        'productos_sin_stock': Inventario.objects.filter(cantidad_disponible=0).count(),
        'productos_con_stock': Inventario.objects.filter(cantidad_disponible__gt=5).count(),
        
        # Producción y pedidos relevantes
        'produccion_proceso': Produccion.objects.filter(estado_produccion='EN PROCESO').count(),
        'pedidos_pendientes': Pedido.objects.filter(estado_pedido='PENDIENTE').count(),
        
        # Listas detalladas para tablas
        'productos_bajo_stock_lista': productos_bajo_stock_lista,
        'productos_sin_stock_lista': productos_sin_stock_lista,
        'produccion_reciente': produccion_reciente,
    }
    
    return render(request, 'dashboard/bodega.html', context)


# =============================================================================
# === LOGOUT ===
# =============================================================================
def logout_view(request):
    """
    Cierra la sesión del usuario y redirige al login.
    Limpia la sesión para evitar datos residuales.
    """
    django_logout(request)
    request.session.flush()
    
    # Manejar redirección con parámetro 'next' si existe
    next_url = request.GET.get('next') or request.POST.get('next')
    
    if next_url:
        return redirect(next_url)
    
    return redirect('usuarios:login')