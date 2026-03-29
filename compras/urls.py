from django.urls import path
from .views import (
    CompraListView, CompraCreateView, CompraUpdateView, CompraDeleteView,
    DetalleCompraCreateView, CompraDetailView, CompraAgregarProductoView, CompraRecibirView, CompraCancelarView,
    DetalleCompraDeleteView, 
)
app_name = 'compras'

urlpatterns = [
    path('', CompraListView.as_view(), name='compra_list'),
    path('nueva/', CompraCreateView.as_view(), name='compra_create'),
    path('compras/<int:pk>/', CompraDetailView.as_view(), name='compra_detail'),
    path('<int:pk>/editar/', CompraUpdateView.as_view(), name='compra_update'),
    path('<int:pk>/eliminar/', CompraDeleteView.as_view(), name='compra_delete'),
    path('<int:pk>/recibir/', CompraRecibirView.as_view(), name='compra_recibir'),
    path('<int:pk>/cancelar/', CompraCancelarView.as_view(), name='compra_cancelar'),
    path('<int:pk>/agregar-producto/', CompraAgregarProductoView.as_view(), name='compra_agregar_producto'),
    
    # Detalle compra
    path('detalle/nuevo/', DetalleCompraCreateView.as_view(), name='detalle_compra_create'),
    path('detalle/<int:pk>/eliminar/', DetalleCompraDeleteView.as_view(), name='detalle_compra_delete'),
]