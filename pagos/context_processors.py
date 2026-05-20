from django.conf import settings


def stripe_settings(request):
    """
    Inyecta la clave pública de Stripe en todos los templates.
    Agregar en settings.py → TEMPLATES → OPTIONS → context_processors:
        'pagos.context_processors.stripe_settings',
    """
    return {
        'STRIPE_PUBLIC_KEY': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
    }