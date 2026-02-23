"""
URL configuration for orden_rae project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from pagina import views as pagina_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs de auth de Django (sin namespace - están en root)
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='pagina/login.html', 
        next_page='pagina:home'       
    ), name='login'),

    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='/'
    ), name='logout'), 
    
    path('accounts/password-reset/', auth_views.PasswordResetView.as_view(
        template_name='pagina/password_reset.html'
    ), name='password_reset'),

    # Registro (sin namespace - está en root)
    path('registro/', pagina_views.registro_view, name='registro'),
    
    # INCLUYE NAMESPACES AQUÍ (esto es lo que faltaba) 
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('pagina.urls', namespace='pagina')),

    #  Otras apps con namespaces
    path('produccion/', include('produccion.urls', namespace='produccion')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('ventas/', include('ventas.urls', namespace='ventas')),
    path('compras/', include('compras.urls', namespace='compras')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
]