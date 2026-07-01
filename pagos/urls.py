from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('iniciar-transaccion/', views.iniciar_transaccion, name='iniciar_transaccion'),
    path('confirmar-pago/', views.confirmar_pago, name='confirmar_pago'),
    path('webhook/', views.wompi_webhook, name='wompi_webhook'),
    path('exito/', views.pago_exitoso, name='pago_exitoso'),

    # Solo disponible con DEBUG=True — para verificar configuración
    path('debug-wompi/', views.debug_wompi, name='debug_wompi'),
]