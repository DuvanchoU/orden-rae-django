from django.contrib import admin
from django.utils.html import format_html
from .models import TransaccionWompi

@admin.register(TransaccionWompi)
class TransaccionWompiAdmin(admin.ModelAdmin):
    """Administración del modelo TransaccionWompi"""
    
    # Columnas visibles en la lista (usando tus campos reales)
    list_display = [
        'id_transaccion',
        'referencia',
        'venta',
        'monto',
        'estado_coloreado',  # Método personalizado con badge de color
        'metodo_pago',
        'es_sandbox',
        'fecha_creacion'
    ]
    
    # Filtros laterales (campos que existen en el modelo)
    list_filter = ['estado', 'metodo_pago', 'es_sandbox', 'fecha_creacion']
    
    # Campos buscables
    search_fields = ['referencia', 'wompi_transaction_id', 'venta__id']
    
    # Campos de solo lectura (todos existen en tu modelo)
    readonly_fields = [
        'wompi_transaction_id',
        'referencia',
        'monto',
        'estado',
        'fecha_creacion',
        'fecha_actualizacion',
        'respuesta_wompi'
    ]
    
    # Agrupación visual de campos en el formulario
    fieldsets = (
        ('Información de Wompi', {
            'fields': ('wompi_transaction_id', 'referencia', 'respuesta_wompi')
        }),
        ('Detalles de la transacción', {
            'fields': ('venta', 'monto', 'estado', 'metodo_pago', 'es_sandbox')
        }),
        ('Metadatos', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    # Prevenir eliminación accidental de transacciones
    def has_delete_permission(self, request, obj=None):
        return False
    
    # Método para mostrar el estado con badge de color
    @admin.display(description='Estado', ordering='estado')
    def estado_coloreado(self, obj):
        """Muestra el estado con badge de color"""
        colores = {
            'PENDIENTE': '#3b82f6',    # Azul
            'APROBADA': '#22c55e',   # Verde
            'RECHAZADA': '#ef4444',   # Rojo
            'ANULADA': '#6b7280',     # Gris
        }
        color = colores.get(obj.estado, '#6b7280')
        label = dict(TransaccionWompi.ESTADOS).get(obj.estado, obj.estado)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color, label
        )