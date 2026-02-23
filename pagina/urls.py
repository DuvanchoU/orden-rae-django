# 📁 pagina/urls.py

from django.urls import path
from . import views

app_name = 'pagina'

urlpatterns = [
    path('', views.home, name='home'),
    path('producto/', views.lista_productos, name='productos'),
    path('carrito-compra/', views.carrito_compra, name='carrito_compra'),
    path('promociones/', views.promociones, name='promociones'),
    path('contacto/', views.contacto, name='contacto'),
    path('cotiza/', views.cotiza, name='cotiza'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    
    # API
    path('api/carrito/agregar/', views.api_agregar_carrito, name='api_agregar_carrito'),
    path('api/notificaciones/', views.api_listar_notificaciones, name='api_listar_notificaciones'),
    path('api/notificaciones/crear/', views.api_crear_notificacion, name='api_crear_notificacion'),
    path('api/notificaciones/marcar-leidas/', views.api_marcar_leidas, name='api_marcar_leidas'),
]