from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [

    # ── Carrito (vistas web) ──────────────────────────────────────────────
    path('carrito/', views.carrito_compra, name='carrito_compra'),
    path('carrito/agregar/', views.carrito_agregar, name='carrito_agregar'),
    path('carrito/actualizar/<int:item_id>/', views.carrito_actualizar, name='carrito_actualizar'),
    path('carrito/eliminar/<int:item_id>/', views.carrito_eliminar, name='carrito_eliminar'),
    path('carrito/limpiar/', views.carrito_limpiar, name='carrito_limpiar'),

    # ── Carrito (API AJAX) ────────────────────────────────────────────────
    path('api/carrito/agregar/', views.api_carrito_agregar, name='api_carrito_agregar'),
    path('api/carrito/actualizar/<int:item_id>/', views.api_carrito_actualizar, name='api_carrito_actualizar'),
    path('api/carrito/eliminar/<int:item_id>/', views.api_carrito_eliminar, name='api_carrito_eliminar'),
    path('api/carrito/contador/', views.api_carrito_contador, name='api_carrito_contador'),

    # ── Clientes ──────────────────────────────────────────────────────────
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/eliminar/', views.ClienteDeleteView.as_view(), name='cliente_delete'),
    path('clientes/<int:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('clientes/<int:pk>/activar/', views.ClienteActivarView.as_view(), name='cliente_activar'),
    path('clientes/<int:pk>/desactivar/', views.ClienteDesactivarView.as_view(), name='cliente_desactivar'),

    # ── Pedidos ───────────────────────────────────────────────────────────
    path('pedidos/', views.PedidoListView.as_view(), name='pedido_list'),
    path('pedidos/nuevo/', views.PedidoCreateView.as_view(), name='pedido_create'),
    path('pedidos/<int:pk>/editar/', views.PedidoUpdateView.as_view(), name='pedido_update'),
    path('pedidos/<int:pk>/eliminar/', views.PedidoDeleteView.as_view(), name='pedido_delete'),
    path('pedidos/<int:pk>/', views.PedidoDetailView.as_view(), name='pedido_detail'),
    path('pedidos/<int:pk>/agregar-producto/', views.PedidoAgregarProductoView.as_view(), name='pedido_agregar_producto'),
    path('pedidos/<int:pk>/cambiar-estado/', views.PedidoCambiarEstadoView.as_view(), name='pedido_cambiar_estado'),

    # ── Ventas ────────────────────────────────────────────────────────────
    path('ventas/', views.VentaListView.as_view(), name='venta_list'),
    path('ventas/nueva/', views.VentaCreateView.as_view(), name='venta_create'),
    path('ventas/<int:pk>/editar/', views.VentaUpdateView.as_view(), name='venta_update'),
    path('ventas/<int:pk>/eliminar/', views.VentaDeleteView.as_view(), name='venta_delete'),
    path('ventas/<int:pk>/', views.VentaDetailView.as_view(), name='venta_detail'),
    path('ventas/<int:pk>/completar/', views.VentaCompletarView.as_view(), name='venta_completar'),

    # ── Cotizaciones ──────────────────────────────────────────────────────
    path('cotizaciones/', views.CotizacionListView.as_view(), name='cotizacion_list'),
    path('cotizaciones/nueva/', views.CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('cotizaciones/<int:pk>/editar/', views.CotizacionUpdateView.as_view(), name='cotizacion_update'),
    path('cotizaciones/<int:pk>/eliminar/', views.CotizacionDeleteView.as_view(), name='cotizacion_delete'),
    path('cotizaciones/<int:pk>/', views.CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('cotizaciones/<int:pk>/enviar/', views.CotizacionEnviarView.as_view(), name='cotizacion_enviar'),
    path('cotizaciones/<int:pk>/aceptar/', views.CotizacionAceptarView.as_view(), name='cotizacion_aceptar'),
    path('cotizaciones/<int:pk>/convertir/', views.CotizacionConvertirVentaView.as_view(), name='cotizacion_convertir'),

    # ── Perfil ────────────────────────────────────────────────────────────
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('perfil/password/', views.password_cambiar, name='password_cambiar'),
    path('perfil/stats/', views.perfil_stats,name='perfil_stats'),
    path('perfil/exportar/', views.datos_exportar, name='datos_exportar'),
    path('perfil/notificaciones/leidas/', views.notificaciones_marcar_leidas, name='notificaciones_marcar_leidas'),
    path('perfil/preferencias/', views.preferencias_guardar, name='preferencias_guardar'),
]