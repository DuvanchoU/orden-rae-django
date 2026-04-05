# pagina/urls.py
from django.urls import path
from . import views

app_name = 'pagina'

urlpatterns = [
    path('', views.home, name='home'),
    path('productos/', views.productos, name='productos'),
    path('productos/<slug:categoria_slug>/', views.productos_por_categoria, name='productos_por_categoria'),
    path('promociones/', views.promociones, name='promociones'),
    
    # Sobre la empresa
    path('quienes-somos/', views.quienes_somos, name='quienes_somos'),
    path('nuestra-historia/', views.nuestra_historia, name='nuestra_historia'),
    path('sostenibilidad/', views.sostenibilidad, name='sostenibilidad'),
    path('trabaja-con-nosotros/', views.trabaja_con_nosotros, name='trabaja_con_nosotros'),
    path('blog-decoracion/', views.blog_decoracion, name='blog_decoracion'),   
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),

    # Usuario y Autenticación
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('api/actualizar-avatar/', views.actualizar_avatar, name='actualizar_avatar'),

    # Formularios
    path('contacto/', views.contacto, name='contacto'),
    path('cotiza/', views.cotiza, name='cotiza'), 
    
    # API
    path('api/carrito/agregar/', views.api_agregar_carrito, name='api_carrito_agregar'),
    path('api/checkout/procesar/', views.api_checkout_procesar, name='api_checkout_procesar'),
    path('api/cotiza/enviar/', views.api_cotiza_enviar, name='api_cotiza_enviar'),
    path('api/contacto/enviar/', views.api_contacto_enviar, name='api_contacto_enviar'),
    path('api/wishlist/toggle/', views.api_wishlist_toggle, name='api_wishlist_toggle'),
    path('api/spin-to-win/', views.api_spin_to_win, name='api_spin_to_win'),
    path('api/notificaciones/', views.api_listar_notificaciones, name='api_listar_notificaciones'),
    path('api/notificaciones/crear/', views.api_crear_notificacion, name='api_crear_notificacion'),
    path('api/notificaciones/marcar-leidas/', views.api_marcar_leidas, name='api_marcar_leidas'),
]