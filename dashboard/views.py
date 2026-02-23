# dashboard/views.py
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth import logout
from produccion.models import Produccion
from ventas.models import Pedido, Ventas
from inventario.models import Producto


class DashboardView(TemplateView):
    """Vista principal del dashboard"""
    template_name = 'dashboard/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_produccion'] = Produccion.objects.count()
        context['total_pedidos'] = Pedido.objects.count()
        context['total_ventas'] = Ventas.objects.count()
        context['total_productos'] = Producto.objects.count()
        return context


def logout_view(request):
    """Cerrar sesión desde el dashboard"""
    logout(request)
    
    # Obtener URL de redirección
    next_url = request.GET.get('next') or request.POST.get('next')
    
    if next_url:
        return redirect(next_url)
    
    return redirect('pagina:index') 