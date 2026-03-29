from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
# Configuración para servir archivos multimedia durante el desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)