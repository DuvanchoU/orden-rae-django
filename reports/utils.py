from django.utils import timezone

def get_report_filename(prefix='reporte'):
    """Genera nombre de archivo con fecha"""
    fecha = timezone.now().strftime('%Y%m%d')
    return f"{prefix}_{fecha}"

def format_currency(value):
    """Formatea moneda para reportes"""
    return f"${value:,.0f}".replace(',', '.')