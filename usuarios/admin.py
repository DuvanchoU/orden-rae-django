from django.contrib import admin
# Register your models here.

from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import Usuarios, RolesOld

@admin.register(RolesOld)
class RolesOldAdmin(admin.ModelAdmin):
    list_display = ['id_rol', 'nombre_rol', 'descripcion', 'created_at']
    search_fields = ['nombre_rol', 'descripcion']
    list_filter = ['created_at']
    ordering = ['nombre_rol']


@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
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
            'fields': ('contrasena_usuario', 'estado')
        }),
        ('Rol y Fechas', {
            'fields': ('id_rol', 'fecha_registro', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Encripta la contraseña si se está creando un nuevo usuario
        Ajusta según tu método de hash (SHA256, bcrypt, etc.)
        """
        if not change and obj.contrasena_usuario:
            # Opción A: Si usas SHA256 (como en el login_view)
            import hashlib
            obj.contrasena_usuario = hashlib.sha256(obj.contrasena_usuario.encode()).hexdigest()
            
            # Opción B: Si usas Django Password Hasher (descomentar si aplica)
            # obj.contrasena_usuario = make_password(obj.contrasena_usuario)
            
        super().save_model(request, obj, form, change)
