from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ADMIN
    path('admin/', admin.site.urls),
    
    # APLICACIONES PRINCIPALES
    path('', include('pagina.urls')),                
    path('dashboard/', include('dashboard.urls')), 

    # OTRAS APLICACIONES
    path('produccion/', include('produccion.urls', namespace='produccion')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('ventas/', include('ventas.urls')),
    path('compras/', include('compras.urls', namespace='compras')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')), # staff → /usuarios/login/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)