from django.urls import path
from .views import (
    CompraListView, CompraCreateView, CompraUpdateView, CompraDeleteView,
    DetalleCompraCreateView,
)
app_name = 'compras'

urlpatterns = [
    path('', CompraListView.as_view(), name='compra_list'),
    path('nueva/', CompraCreateView.as_view(), name='compra_create'),
    path('<int:pk>/editar/', CompraUpdateView.as_view(), name='compra_update'),
    path('<int:pk>/eliminar/', CompraDeleteView.as_view(), name='compra_delete'),
    path('detalle/nuevo/', DetalleCompraCreateView.as_view(), name='detalle_compra_create'),
]