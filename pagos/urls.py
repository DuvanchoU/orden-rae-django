from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('crear-payment-intent/', views.crear_payment_intent, name='crear_payment_intent'),
    path('confirmar-pago/', views.confirmar_pago, name='confirmar_pago'),
    path('webhook/',  views.stripe_webhook, name='stripe_webhook'),
    path('exito/', views.pago_exitoso, name='pago_exitoso'),

    # Solo disponible con DEBUG=True — para verificar configuración
    path('debug-stripe/', views.debug_stripe, name='debug_stripe'),
]