# config/urls.py
from django.contrib import admin
from django.urls import path, include

# IMPORTAR VISTAS PERSONALIZADAS
from usuarios.views import login_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # VISTAS PERSONALIZADAS 
    path('login/', login_view, name='login'),      
    path('logout/', logout_view, name='logout'),   
    
    # INCLUYE NAMESPACES
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('pagina.urls', namespace='pagina')),

    # Otras apps con namespaces
    path('produccion/', include('produccion.urls', namespace='produccion')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('ventas/', include('ventas.urls')),
    path('compras/', include('compras.urls', namespace='compras')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
]