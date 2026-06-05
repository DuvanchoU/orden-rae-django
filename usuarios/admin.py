from django.contrib import admin
from .models import Usuarios, RolesOld
from .forms import UsuarioAdminForm, RolForm

@admin.register(RolesOld)
class RolesOldAdmin(admin.ModelAdmin):
    form = RolForm  # Usar el formulario de Rol

    list_display = ['id_rol', 'nombre_rol', 'descripcion', 'created_at']
    search_fields = ['nombre_rol', 'descripcion']
    list_filter = ['created_at']
    ordering = ['nombre_rol']


@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
    form = UsuarioAdminForm  # Usar el formulario de Usuario
    
    list_display = [
        'id_usuario', 'nombres', 'apellidos', 'correo_usuario', 
        'documento', 'id_rol', 'estado', 'fecha_registro'
    ]
    list_filter = ['estado', 'id_rol', 'fecha_registro']
    search_fields = ['nombres', 'apellidos', 'correo_usuario', 'documento']
    ordering = ['-fecha_registro']
    list_per_page = 20
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombres', 'apellidos', 'documento', 'correo_usuario', 'telefono', 'genero')
        }),
        ('Credenciales', {
            'fields': ('contrasena_usuario', 'confirmar_contrasena', 'estado')
        }),
        ('Rol y Fechas', {
            'fields': ('id_rol', 'fecha_registro', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['fecha_registro', 'created_at', 'updated_at']
