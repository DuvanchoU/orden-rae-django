from django.contrib import admin
from django.urls import path, include

# Importar vistas de autenticación personalizada
from usuarios.views import login_view, logout_view

urlpatterns = [
    # ADMIN
    path('admin/', admin.site.urls),
    
    # AUTENTICACIÓN PERSONALIZADA
    path('login/', login_view, name='login'),
    path('usuarios/login/', login_view, name='login'),      
    path('logout/', logout_view, name='logout'),   
    
    # APLICACIONES PRINCIPALES
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('pagina.urls', namespace='pagina')),

    # OTRAS APLICACIONES
    path('produccion/', include('produccion.urls', namespace='produccion')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('ventas/', include('ventas.urls')),
    path('compras/', include('compras.urls', namespace='compras')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
]