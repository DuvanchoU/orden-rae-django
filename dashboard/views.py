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
        return redirect('pagina:login')
    
    rol = request.user.id_rol.nombre_rol
    
    # Mapa de redirección por rol
    rol_dashboard_map = {
        'GERENTE': 'dashboard:dashboard_gerente',
        'ASESOR COMERCIAL': 'dashboard:dashboard_asesor',
        'JEFE LOGISTICO': 'dashboard:dashboard_logistica',
        'AUXILIAR DE BODEGA': 'dashboard:dashboard_bodega',
        'CLIENTE': 'pagina:home'  # Los clientes van al home público
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
        #  CORREGIDO: usa self.request en lugar de request
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
    
    return redirect('pagina:home')

# =============================================================================
# === PERFIL ===
# =============================================================================

from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from usuarios.decorators import login_required_custom


# ─────────────────────────────────────────────
# MAPA DE PERMISOS POR ROL
# ─────────────────────────────────────────────
PERMISOS_POR_ROL = {
    'GERENTE': {
        'can_view_dashboard':    True,
        'can_view_inventario':   True,
        'can_view_ventas':       True,
        'can_view_pedidos':      True,
        'can_view_clientes':     True,
        'can_view_cotizaciones': True,
        'can_view_produccion':   True,
        'can_view_compras':      True,
        'can_view_usuarios':     True,
    },
    'ASESOR COMERCIAL': {
        'can_view_dashboard':    True,
        'can_view_inventario':   True,
        'can_view_ventas':       True,
        'can_view_pedidos':      True,
        'can_view_clientes':     True,
        'can_view_cotizaciones': True,
        'can_view_produccion':   False,
        'can_view_compras':      False,
        'can_view_usuarios':     False,
    },
    'JEFE LOGISTICO': {
        'can_view_dashboard':    True,
        'can_view_inventario':   True,
        'can_view_ventas':       False,
        'can_view_pedidos':      True,
        'can_view_clientes':     False,
        'can_view_cotizaciones': False,
        'can_view_produccion':   True,
        'can_view_compras':      True,
        'can_view_usuarios':     False,
    },
    'AUXILIAR DE BODEGA': {
        'can_view_dashboard':    True,
        'can_view_inventario':   True,
        'can_view_ventas':       False,
        'can_view_pedidos':      False,
        'can_view_clientes':     False,
        'can_view_cotizaciones': False,
        'can_view_produccion':   False,
        'can_view_compras':      False,
        'can_view_usuarios':     False,
    },
}

def _get_permisos(usuario):
    """Devuelve el dict de permisos según el rol del usuario."""
    rol = usuario.id_rol.nombre_rol if usuario.id_rol else ''
    return PERMISOS_POR_ROL.get(rol, {key: False for key in [
        'can_view_dashboard', 'can_view_inventario', 'can_view_ventas',
        'can_view_pedidos', 'can_view_clientes', 'can_view_cotizaciones',
        'can_view_produccion', 'can_view_compras', 'can_view_usuarios',
    ]})


# ─────────────────────────────────────────────
# VISTA PERFIL
# ─────────────────────────────────────────────
@login_required_custom
def perfil_view(request):
    usuario = request.user

    stats = {'ventas': 0, 'pedidos': 0, 'cotizaciones': 0}
    # Si quieres conectar estadísticas reales descomenta:
    # from ventas.models import Ventas, Pedido, Cotizaciones
    # stats['ventas']       = Ventas.objects.filter(...).count()
    # stats['pedidos']      = Pedido.objects.filter(...).count()
    # stats['cotizaciones'] = Cotizaciones.objects.filter(...).count()

    context = {
        'perfil_usuario':   usuario,
        'user_nombre':      usuario.nombres,
        'user_apellido':    usuario.apellidos,
        'user_rol':         usuario.id_rol.nombre_rol if usuario.id_rol else 'Sin rol',
        'user_permissions': _get_permisos(usuario),
        'stats':            stats,
        'actividad_reciente': [],
    }
    return render(request, 'dashboard/perfil.html', context)


# ─────────────────────────────────────────────
# VISTA ACTUALIZAR PERFIL
# ─────────────────────────────────────────────
@login_required_custom
@require_POST
def perfil_update_view(request):
    usuario = request.user
    action  = request.POST.get('action')

    # ── Actualizar información personal ──────
    if action == 'update_info':
        nombres  = request.POST.get('first_name', '').strip()
        apellidos = request.POST.get('last_name', '').strip()
        correo   = request.POST.get('email', '').strip().lower()
        telefono = request.POST.get('telefono', '').strip()

        if not nombres or len(nombres) < 2:
            messages.error(request, 'El nombre debe tener al menos 2 caracteres.')
            return redirect('dashboard:perfil')

        if correo and '@' not in correo:
            messages.error(request, 'El correo electrónico no es válido.')
            return redirect('dashboard:perfil')

        # Verificar que el correo no lo use otro usuario
        from usuarios.models import Usuarios
        if correo and Usuarios.objects.filter(
            correo_usuario=correo
        ).exclude(pk=usuario.pk).exists():
            messages.error(request, 'Ese correo ya está registrado por otro usuario.')
            return redirect('dashboard:perfil')

        usuario.nombres          = nombres
        usuario.apellidos        = apellidos
        usuario.correo_usuario   = correo or usuario.correo_usuario
        if telefono:
            usuario.telefono = telefono

        # Guardamos sin ejecutar full_clean para evitar revalidar contraseña
        usuario.save(update_fields=['nombres', 'apellidos',
                                    'correo_usuario', 'telefono',
                                    'updated_at'])
        messages.success(request, 'Información personal actualizada correctamente.')
        return redirect('dashboard:perfil')

    # ── Cambiar contraseña ────────────────────
    elif action == 'change_password':
        current  = request.POST.get('current_password', '')
        new_pwd  = request.POST.get('new_password', '')
        confirm  = request.POST.get('confirm_password', '')

        if not usuario.check_password(current):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('dashboard:perfil')

        if new_pwd != confirm:
            messages.error(request, 'Las contraseñas nuevas no coinciden.')
            return redirect('dashboard:perfil')

        if len(new_pwd) < 8:
            messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            return redirect('dashboard:perfil')

        try:
            # Usa el método del modelo que ya valida fortaleza y hashea
            usuario.cambiar_contrasena(current, new_pwd)
            messages.success(request, 'Contraseña actualizada correctamente.')
        except Exception as e:
            messages.error(request, str(e))

        return redirect('dashboard:perfil')

    messages.error(request, 'Acción no reconocida.')
    return redirect('dashboard:perfil')
# =============================================================================
# === CHECK DE SESIÓN (ENDPOINT LIVIANO PARA JS) ===
# =============================================================================

from django.http import JsonResponse
# Este endpoint es consultado por el JS del dashboard en cada carga para verificar que la sesión siga siendo válida. 
# Si el usuario ha cerrado sesión en otra pestaña o su sesión ha expirado, el decorador login_required_custom redirigirá al login, 
# y el JS del cliente detectará el redirect y
@login_required_custom
def session_check(request):
    """
    Endpoint liviano que el JS del dashboard consulta en cada carga.
    Si la sesión no es válida, login_required_custom redirige al login
    y el JS del cliente detecta el redirect y manda al login.
    """
    return JsonResponse({'ok': True})