from django.shortcuts import render
from django.views.generic import TemplateView
from produccion.models import Produccion
from ventas.models import Pedido, Ventas
from inventario.models import Producto

class DashboardView(TemplateView):
    template_name = 'dashboard/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_produccion'] = Produccion.objects.count()
        context['total_pedidos'] = Pedido.objects.count()
        context['total_ventas'] = Ventas.objects.count()
        context['total_productos'] = Producto.objects.count()
        return context