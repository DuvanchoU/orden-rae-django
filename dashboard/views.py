# dashboard/views.py
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from produccion.models import Produccion
from ventas.models import Pedido, Ventas, Cotizaciones
from inventario.models import Producto, Inventario
from compras.models import Compras
from usuarios.models import Usuarios


class DashboardView(TemplateView):
    """Vista principal del dashboard"""
    template_name = 'dashboard/home.html'
    
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
        ventas_mes = Ventas.objects.filter(fecha_venta__gte=inicio_mes)
        context['ventas_mes'] = ventas_mes.count()
        context['ingresos_mes'] = ventas_mes.aggregate(total=Sum('total'))['total'] or 0
        
        # === PEDIDOS POR ESTADO ===
        context['pedidos_pendientes'] = Pedido.objects.filter(estado_pedido='PENDIENTE').count()
        context['pedidos_proceso'] = Pedido.objects.filter(estado_pedido='EN PROCESO').count()
        context['pedidos_completados'] = Pedido.objects.filter(estado_pedido='COMPLETADO').count()
        
        # === PRODUCCIÓN POR ESTADO ===
        context['produccion_pendiente'] = Produccion.objects.filter(estado_produccion='PENDIENTE').count()
        context['produccion_proceso'] = Produccion.objects.filter(estado_produccion='EN PROCESO').count()
        context['produccion_terminada'] = Produccion.objects.filter(estado_produccion='TERMINADA').count()
        
        # === PRODUCTOS BAJO STOCK ===
        context['productos_bajo_stock'] = Inventario.objects.filter(cantidad_disponible__lte=5).count()
        
        # === COTIZACIONES POR ESTADO ===
        context['cotizaciones_pendientes'] = Cotizaciones.objects.filter(estado='borrador').count()
        context['cotizaciones_enviadas'] = Cotizaciones.objects.filter(estado='enviada').count()
        context['cotizaciones_aceptadas'] = Cotizaciones.objects.filter(estado='aceptada').count()
        
        # === ÚLTIMAS VENTAS ===
        context['ultimas_ventas'] = Ventas.objects.select_related('cliente').order_by('-fecha_venta')[:5]
        
        # === ÚLTIMOS PEDIDOS ===
        context['ultimos_pedidos'] = Pedido.objects.select_related('cliente').order_by('-fecha_pedido')[:5]
        
        # === DATOS PARA GRÁFICAS ===
        # Ventas por último 6 meses
        context['ventas_6_meses'] = self._get_ventas_por_mes()
        
        # Productos por categoría
        context['productos_por_categoria'] = self._get_productos_por_categoria()
        
        # Estados de pedidos
        context['pedidos_estado_data'] = self._get_pedidos_por_estado()
        
        return context
    
    def _get_ventas_por_mes(self):
        """Obtiene ventas de los últimos 6 meses"""
        hoy = timezone.now()
        datos = []
        etiquetas = []
        
        for i in range(5, -1, -1):
            mes = hoy - timedelta(days=30*i)
            inicio_mes = mes.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fin_mes = inicio_mes + timedelta(days=32)
            fin_mes = fin_mes.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            total = Ventas.objects.filter(
                fecha_venta__gte=inicio_mes,
                fecha_venta__lt=fin_mes
            ).aggregate(total=Sum('total'))['total'] or 0
            
            etiquetas.append(mes.strftime('%b'))
            datos.append(float(total))
        
        return {'etiquetas': etiquetas, 'datos': datos}
    
    def _get_productos_por_categoria(self):
        """Obtiene productos agrupados por categoría"""
        from inventario.models import Categorias
        categorias = Categorias.objects.annotate(
            total_productos=Count('producto')
        ).order_by('-total_productos')[:5]
        
        return {
            'etiquetas': [cat.nombre_categoria for cat in categorias],
            'datos': [cat.total_productos for cat in categorias]
        }
    
    def _get_pedidos_por_estado(self):
        """Obtiene pedidos agrupados por estado"""
        estados = ['PENDIENTE', 'CONFIRMADO', 'EN PROCESO', 'COMPLETADO', 'CANCELADO']
        datos = []
        
        for estado in estados:
            count = Pedido.objects.filter(estado_pedido=estado).count()
            datos.append(count)
        
        return {'etiquetas': estados, 'datos': datos}


def logout_view(request):
    """Cerrar sesión desde el dashboard"""
    logout(request)
    
    next_url = request.GET.get('next') or request.POST.get('next')
    
    if next_url:
        return redirect(next_url)
    
    return redirect('pagina:index')