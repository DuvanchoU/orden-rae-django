from django.urls import path
from .views import (
    ProductoListView, ProductoCreateView, ProductoUpdateView, ProductoDeleteView,
    BodegaListView, BodegaCreateView, BodegaUpdateView, BodegaDeleteView,
    CategoriaListView, CategoriaCreateView, CategoriaUpdateView, CategoriaDeleteView,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView,
    InventarioListView, InventarioCreateView, InventarioUpdateView, InventarioDeleteView,
)

app_name = 'inventario'

urlpatterns = [
    # Productos
    path('productos/', ProductoListView.as_view(), name='producto_list'),
    path('productos/nuevo/', ProductoCreateView.as_view(), name='producto_create'),
    path('productos/<int:pk>/editar/', ProductoUpdateView.as_view(), name='producto_update'),
    path('productos/<int:pk>/eliminar/', ProductoDeleteView.as_view(), name='producto_delete'),
    
    # Bodegas
    path('bodegas/', BodegaListView.as_view(), name='bodega_list'),
    path('bodegas/nueva/', BodegaCreateView.as_view(), name='bodega_create'),
    path('bodegas/<int:pk>/editar/', BodegaUpdateView.as_view(), name='bodega_update'),
    path('bodegas/<int:pk>/eliminar/', BodegaDeleteView.as_view(), name='bodega_delete'),
    
    # Categorías
    path('categorias/', CategoriaListView.as_view(), name='categoria_list'),
    path('categorias/nueva/', CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/', CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<int:pk>/eliminar/', CategoriaDeleteView.as_view(), name='categoria_delete'),
    
    # Proveedores
    path('proveedores/', ProveedorListView.as_view(), name='proveedor_list'),
    path('proveedores/nuevo/', ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/<int:pk>/editar/', ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('proveedores/<int:pk>/eliminar/', ProveedorDeleteView.as_view(), name='proveedor_delete'),
    
    # Inventario (Stock)
    path('stock/', InventarioListView.as_view(), name='inventario_list'),
    path('stock/nuevo/', InventarioCreateView.as_view(), name='inventario_create'),
    path('stock/<int:pk>/editar/', InventarioUpdateView.as_view(), name='inventario_update'),
    path('stock/<int:pk>/eliminar/', InventarioDeleteView.as_view(), name='inventario_delete'),
]