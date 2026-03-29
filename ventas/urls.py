from django.urls import path
from . import views
from .views import (
    ClienteListView, ClienteCreateView, ClienteUpdateView, ClienteDeleteView, ClienteDetailView, ClienteActivarView, ClienteDesactivarView,
    PedidoListView, PedidoCreateView, PedidoUpdateView, PedidoDeleteView,PedidoDetailView,
    VentaListView, VentaCreateView, VentaUpdateView, VentaDeleteView, VentaDetailView,
    CotizacionListView, CotizacionCreateView, CotizacionUpdateView, CotizacionDeleteView, CotizacionDetailView,
)

app_name = 'ventas'

urlpatterns = [
    # Clientes
    path('clientes/', ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/editar/', ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', ClienteDeleteView.as_view(), name='cliente_delete'),
    path('clientes/<int:pk>/activar/', ClienteActivarView.as_view(), name='cliente_activar'),
    path('clientes/<int:pk>/desactivar/', ClienteDesactivarView.as_view(), name='cliente_desactivar'),

    # Pedidos
    path('pedido/', PedidoListView.as_view(), name='pedido_list'),
    path('pedido/nuevo/', PedidoCreateView.as_view(), name='pedido_create'),
    path('pedido/<int:pk>/', PedidoDetailView.as_view(), name='pedido_detail'),
    path('pedido/<int:pk>/editar/', PedidoUpdateView.as_view(), name='pedido_update'),
    path('pedido/<int:pk>/eliminar/', PedidoDeleteView.as_view(), name='pedido_delete'),

    # Ventas
    path('ventas/', VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/', VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/editar/', VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', VentaDeleteView.as_view(), name='venta_delete'),

    # Cotizaciones
    path('cotizaciones/', CotizacionListView.as_view(), name='cotizacion_list'),
    path('cotizaciones/nueva/', CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('cotizaciones/<int:pk>/', CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('cotizaciones/<int:pk>/editar/', CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('cotizaciones/<int:pk>/eliminar/', CotizacionDeleteView.as_view(), name='cotizacion_delete'),

    # Carrito
    path('carrito/', views.carrito_compra, name='carrito_compra'),
    path('carrito/agregar/', views.api_carrito_agregar, name='carrito_agregar'),
    path('carrito/eliminar/<int:item_id>/', views.api_carrito_eliminar, name='carrito_eliminar'),
    path('carrito/actualizar/<int:item_id>/', views.api_carrito_actualizar, name='carrito_actualizar'),
    path('api/carrito/agregar/', views.api_carrito_agregar, name='api_carrito_agregar'),
    path('api/carrito/contador/', views.api_carrito_contador, name='api_carrito_contador'),

     # Perfil
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('perfil/actualizar/', views.perfil_actualizar, name='perfil_actualizar'),
    path('perfil/avatar/', views.avatar_actualizar, name='avatar_actualizar'),
    path('perfil/password/', views.password_cambiar, name='password_cambiar'),
    path('perfil/notificaciones/leidas/', views.notificaciones_marcar_leidas, name='notificaciones_marcar_leidas'),
    path('perfil/preferencias/', views.preferencias_guardar, name='preferencias_guardar'),
    path('perfil/exportar/', views.datos_exportar, name='datos_exportar'),
    path('perfil/stats/', views.perfil_stats, name='perfil_stats'), 
]