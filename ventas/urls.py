from django.urls import path
from .views import (
    ClienteListView, ClienteCreateView, ClienteUpdateView, ClienteDeleteView, ClienteDetailView,
    PedidoListView, PedidoCreateView, PedidoUpdateView, PedidoDeleteView,PedidoDetailView,
    VentaListView, VentaCreateView, VentaUpdateView, VentaDeleteView,
    CotizacionListView, CotizacionCreateView, CotizacionUpdateView, CotizacionDeleteView,
)

app_name = 'ventas'

urlpatterns = [
    # Clientes
    path('clientes/', ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/editar/', ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', ClienteDeleteView.as_view(), name='cliente_delete'),

    # Pedidos
    path('pedido/', PedidoListView.as_view(), name='pedido_list'),
    path('pedido/nuevo/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedido/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
    path('pedido/<int:pk>/editar/', PedidoUpdateView.as_view(), name='pedido_update'),
    path('pedido/<int:pk>/eliminar/', PedidoDeleteView.as_view(), name='pedido_delete'),

    # Ventas
    path('ventas/', VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/editar/', VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', VentaDeleteView.as_view(), name='venta_delete'),

    # Cotizaciones
    path('cotizaciones/', CotizacionListView.as_view(), name='cotizacion_list'),
    path('cotizaciones/nueva/', CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('cotizaciones/<int:pk>/editar/', CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('cotizaciones/<int:pk>/eliminar/', CotizacionDeleteView.as_view(), name='cotizacion_delete'),
]