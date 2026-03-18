from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from xhtml2pdf import pisa
import os

def link_callback(uri, rel):
    """
    Convierte rutas de /static/ y /media/ a rutas absolutas del sistema
    """
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    elif uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        return uri

    if not os.path.isfile(path):
        raise Exception(f"Media URI no encontrada: {path}")

    return path


class PDFReportGenerator:
    
    def __init__(self, template_name, context, filename):
        self.template_name = template_name
        self.context = context
        self.filename = filename
    
    def render_to_response(self):
        html_string = render_to_string(self.template_name, self.context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{self.filename}.pdf"'

        pisa_status = pisa.CreatePDF(
            html_string,
            dest=response,
            link_callback=link_callback
        )

        if pisa_status.err:
            return HttpResponse(f'Error al generar PDF', status=500)

        return response