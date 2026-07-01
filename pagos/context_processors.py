from django.conf import settings


def wompi_settings(request):
    """
    Inyecta la llave pública de Wompi en todos los templates.
    Configurado en settings.py -> TEMPLATES -> OPTIONS -> context_processors:
        'pagos.context_processors.wompi_settings',
    """
    return {
        'WOMPI_PUBLIC_KEY': getattr(settings, 'WOMPI_PUBLIC_KEY', ''),
        'WOMPI_CURRENCY':   getattr(settings, 'WOMPI_CURRENCY', 'COP'),
    }