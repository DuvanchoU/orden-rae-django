# reports/generators/mixins.py
from django.http import HttpResponse, HttpResponseBadRequest
from .pdf_generator import PDFReportGenerator
from .excel_generator import ExcelReportGenerator
import csv

class ReportMixin:
    report_formats = ['pdf', 'excel', 'csv']
    
    # Intercepta la petición GET
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format')
        if format_type in self.report_formats:
            return self.render_report(format_type)
        # Si no es reporte, comporta como una ListView normal
        return super().get(request, *args, **kwargs)

    def get_report_data(self):
        raise NotImplementedError("Debes implementar get_report_data() en tu vista")
    
    def get_report_template(self):
        return 'reports/base_report.html'
    
    def render_report(self, format_type):
        try:
            report_data = self.get_report_data()
            
            if format_type == 'pdf':
                return self._generate_pdf(report_data)
            elif format_type == 'excel':
                return self._generate_excel(report_data)
            elif format_type == 'csv':
                return self._generate_csv(report_data)
        except Exception as e:
            # Muestra el error real en el navegador para depurar
            return HttpResponseBadRequest(f"Error generando reporte: {str(e)}")
    
    def _generate_pdf(self, report_data):
        generator = PDFReportGenerator(
            template_name=self.get_report_template(),
            context=report_data.get('context', {}),
            filename=report_data.get('filename', 'reporte')
        )
        return generator.render_to_response()
    
    def _generate_excel(self, report_data):
        generator = ExcelReportGenerator(
            filename=report_data.get('filename', 'reporte'),
            headers=report_data['headers'],
            data=report_data['rows']
        )
        return generator.generate()
    
    def _generate_csv(self, report_data):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_data.get("filename", "reporte")}.csv"'
        writer = csv.writer(response)
        writer.writerow(report_data['headers'])
        writer.writerows(report_data['rows'])
        return response