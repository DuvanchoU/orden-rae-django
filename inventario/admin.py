from django.contrib import admin
from .models import Bodegas, Categorias, Proveedores, Producto, Inventario, ImagenesProducto


@admin.register(Bodegas)
class BodegasAdmin(admin.ModelAdmin):
    list_display = ['id_bodega', 'nombre_bodega', 'estado', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['nombre_bodega']
    ordering = ['nombre_bodega']


@admin.register(Categorias)
class CategoriasAdmin(admin.ModelAdmin):
    list_display = ['id_categorias', 'nombre_categoria', 'estado_categoria', 'created_at']
    list_filter = ['estado_categoria', 'created_at']
    search_fields = ['nombre_categoria']
    ordering = ['nombre_categoria']


@admin.register(Proveedores)
class ProveedoresAdmin(admin.ModelAdmin):
    list_display = ['id_proveedor', 'nombre', 'telefono', 'email', 'estado', 'created_at']
    list_filter = ['estado', 'created_at']
    search_fields = ['nombre', 'email', 'telefono']
    ordering = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'id_producto', 'codigo_producto', 'referencia_producto', 
        'categoria', 'precio_actual', 'estado', 'created_at'
    ]
    list_filter = ['estado', 'categoria', 'created_at']
    search_fields = ['codigo_producto', 'referencia_producto']
    ordering = ['-created_at']
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_producto', 'referencia_producto', 'categoria')
        }),
        ('Detalles', {
            'fields': ('proveedor_id', 'tipo_madera', 'color_producto', 'precio_actual')
        }),
        ('Estado y Fechas', {
            'fields': ('estado', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = [
        'id_inventario', 'producto', 'bodega', 'proveedor', 
        'cantidad_disponible', 'cantidad_reservada', 'estado', 'fecha_registro'
    ]
    list_filter = ['estado', 'bodega', 'fecha_registro']
    search_fields = ['producto__codigo_producto', 'producto__referencia_producto']
    ordering = ['-fecha_registro']
    list_per_page = 20
    
    fieldsets = (
        ('Información del Inventario', {
            'fields': ('producto', 'bodega', 'proveedor')
        }),
        ('Cantidades', {
            'fields': ('cantidad_disponible', 'cantidad_reservada', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_llegada', 'fecha_registro', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_registro', 'created_at', 'updated_at']


@admin.register(ImagenesProducto)
class ImagenesProductoAdmin(admin.ModelAdmin):
    list_display = ['id_imagen', 'producto', 'descripcion', 'es_principal', 'created_at']
    list_filter = ['es_principal', 'producto', 'created_at']
    search_fields = ['producto__codigo_producto', 'descripcion']
    ordering = ['-created_at']
    list_per_page = 20
    
    fieldsets = (
        ('Información de la Imagen', {
            'fields': ('producto', 'ruta_imagen', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('es_principal', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    # IMPORTANTE: Permitir subida de archivos
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Asegurar que el campo de archivo tenga el widget correcto
        if 'ruta_imagen' in form.base_fields:
            from django.forms import ClearableFileInput
            form.base_fields['ruta_imagen'].widget = ClearableFileInput()
        return form
