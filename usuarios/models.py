from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import re

class RolesOld(models.Model):
    ROLES_SISTEMA = [
        ('GERENTE', 'Gerente'),
        ('ASESOR COMERCIAL', 'Asesor Comercial'),
        ('JEFE LOGISTICO', 'Jefe Logístico'),
        ('AUXILIAR DE BODEGA', 'Auxiliar de Bodega'),
        ('CLIENTE', 'Cliente'),
    ]

    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(unique=True, max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'roles_old'
        ordering = ['nombre_rol']

    def clean(self):
        """Validaciones del rol"""
        if self.nombre_rol and len(self.nombre_rol.strip()) < 3:
            raise ValidationError("El nombre del rol debe tener al menos 3 caracteres")
        
        # Validar que no se elimine un rol del sistema
        if self.pk and self.nombre_rol in dict(self.ROLES_SISTEMA):
            raise ValidationError(f"No se puede eliminar o modificar el rol del sistema '{self.nombre_rol}'")

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        if self.nombre_rol in dict(self.ROLES_SISTEMA):
            raise ValidationError(f"No se puede eliminar el rol del sistema '{self.nombre_rol}'")
        
        # Verificar si hay usuarios con este rol
        if self.usuarios_set.filter(deleted_at__isnull=True).exists():
            raise ValidationError("No se puede eliminar un rol que tiene usuarios asignados")
        
        self.deleted_at = timezone.now()
        self.save()
        return self

    def puede_eliminarse(self):
        """Verifica si el rol puede eliminarse"""
        if self.nombre_rol in dict(self.ROLES_SISTEMA):
            return False
        return not self.usuarios_set.filter(deleted_at__isnull=True).exists()

    def get_total_usuarios(self):
        """Obtiene la cantidad de usuarios con este rol"""
        return self.usuarios_set.filter(
            deleted_at__isnull=True
        ).count()

    def __str__(self):
        return self.nombre_rol
    
class Usuarios(models.Model):
    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]
    
    ESTADOS_USUARIO = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('SUSPENDIDO', 'Suspendido'),
    ]
    foto_perfil = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True, 
        default='avatars/default-avatar-1.png'
    )
    id_usuario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    documento = models.CharField(unique=True, max_length=20)
    correo_usuario = models.CharField(unique=True, max_length=255)
    contrasena_usuario = models.CharField(max_length=255)
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS_USUARIO,
        default='ACTIVO'
    )
    fecha_registro = models.DateTimeField(default=timezone.now)
    id_rol = models.ForeignKey(
        RolesOld, 
        models.DO_NOTHING, 
        db_column='id_rol',
        related_name='usuarios'
    )
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='último login')
    
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    class Meta:
        managed = True
        db_table = 'usuarios'
        ordering = ['nombres']
        indexes = [
            models.Index(fields=['correo_usuario']),
            models.Index(fields=['documento']),
            models.Index(fields=['estado']),
        ]
    
    def clean(self):
        """Validaciones del usuario"""
        # Validar nombres
        if not self.nombres or len(self.nombres.strip()) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres")
        
        # Validar apellidos
        if not self.apellidos or len(self.apellidos.strip()) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres")
        
        # Validar documento
        if self.documento:
            self.documento = self.documento.strip()
            if len(self.documento) < 5:
                raise ValidationError("El documento debe tener al menos 5 caracteres")
            if not self.documento.replace('-', '').replace('.', '').isdigit():
                raise ValidationError("El documento solo debe contener números")
        
        # Validar email
        if self.correo_usuario:
            self.correo_usuario = self.correo_usuario.lower().strip()
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, self.correo_usuario):
                raise ValidationError("El correo electrónico no es válido")
        
        # Validar teléfono
        if self.telefono:
            self.telefono = self.telefono.strip()
            telefono_limpio = re.sub(r'[^\d+]', '', self.telefono)
            if len(telefono_limpio) < 7:
                raise ValidationError("El teléfono debe tener al menos 7 dígitos")
            if len(telefono_limpio) > 15:
                raise ValidationError("El teléfono no puede tener más de 15 dígitos")
        
        # Validar contraseña (solo en creación o si se está cambiando)
        if self.pk:
            try:
                original = Usuarios.objects.get(pk=self.pk)
                if original.contrasena_usuario != self.contrasena_usuario:
                    self._validar_fortaleza_contrasena()
            except Usuarios.DoesNotExist:
                self._validar_fortaleza_contrasena()
        else:
            self._validar_fortaleza_contrasena()

    def _validar_fortaleza_contrasena(self):
        """Valida que la contraseña cumpla con los requisitos de seguridad"""
        if not self.contrasena_usuario:
            raise ValidationError("La contraseña es obligatoria")
        
        if len(self.contrasena_usuario) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres")
        
        if not re.search(r'[A-Z]', self.contrasena_usuario):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula")
        
        if not re.search(r'[a-z]', self.contrasena_usuario):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula")
        
        if not re.search(r'\d', self.contrasena_usuario):
            raise ValidationError("La contraseña debe contener al menos un número")

    def save(self, *args, **kwargs):
        """Auto-gestión de timestamps y hash de contraseña"""
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            self.fecha_registro = timezone.now()
        
        self.updated_at = timezone.now()
        
        # Hashear contraseña si es nueva o cambió
        if self.contrasena_usuario and not self.contrasena_usuario.startswith('pbkdf2_'):
            self.contrasena_usuario = make_password(self.contrasena_usuario)
        
        update_fields = kwargs.get('update_fields')
        if update_fields is None:
            self.full_clean()
        
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.estado = 'INACTIVO'
        self.save()
        return self

    def hard_delete(self):
        """Eliminación física solo si no es último administrador"""
        if self.id_rol and self.id_rol.nombre_rol == 'GERENTE':
            if Usuarios.objects.filter(
                id_rol__nombre_rol='GERENTE',
                deleted_at__isnull=True
            ).count() <= 1:
                raise ValidationError("No se puede eliminar el último usuario con rol de Gerente")
        super().delete()

    def restore(self):
        """Restaurar usuario eliminado"""
        self.deleted_at = None
        self.estado = 'ACTIVO'
        self.save()

    # =====================================================================
    # MÉTODOS DE AUTENTICACIÓN SEGUROS
    # =====================================================================
    
    def check_password(self, raw_password):
        """Verifica si la contraseña proporcionada es correcta"""
        return check_password(raw_password, self.contrasena_usuario)

    def set_password(self, raw_password):
        """Establece una nueva contraseña con hash"""
        self.contrasena_usuario = make_password(raw_password)
        self.ultimo_cambio_contrasena = timezone.now()
        self.debe_cambiar_contrasena = False

    def cambiar_contrasena(self, old_password, new_password):
        """Cambia la contraseña validando la anterior"""
        if not self.check_password(old_password):
            raise ValidationError("La contraseña actual es incorrecta")
        
        # Validar fortaleza de nueva contraseña
        self.contrasena_usuario = new_password
        self._validar_fortaleza_contrasena()
        self.set_password(new_password)
        self.save()

    def registrar_ultimo_login(self):
        """Registra el último inicio de sesión"""
        self.ultimo_login = timezone.now()
        self.save(update_fields=['ultimo_login'])

    # =====================================================================
    # PROPIEDADES PARA COMPATIBILIDAD CON DJANGO
    # =====================================================================
    
    @property
    def username(self):
        return self.correo_usuario
    
    @property
    def email(self):
        return self.correo_usuario
    
    @property
    def is_authenticated(self):
        return self.estado == 'ACTIVO' and self.deleted_at is None 
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return self.estado == 'ACTIVO' and self.deleted_at is None
    
    @property
    def is_superuser(self):
        if self.id_rol:
            return self.id_rol.nombre_rol == 'GERENTE'
        return False
    
    @property
    def is_staff(self):
        if self.id_rol:
            return self.id_rol.nombre_rol != 'CLIENTE'
        return False

    # =====================================================================
    # MÉTODOS DE PERMISOS
    # =====================================================================
    
    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return True
    
    def has_module_perms(self, app_label):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        
        permisos_por_rol = {
            'GERENTE': ['admin', 'auth', 'contenttypes', 'sessions', 'usuarios', 'dashboard', 'inventario', 'ventas', 'compras', 'produccion'],
            'ASESOR COMERCIAL': ['usuarios', 'dashboard', 'inventario', 'ventas'],
            'JEFE LOGISTICO': ['usuarios', 'dashboard', 'inventario', 'produccion'],
            'AUXILIAR DE BODEGA': ['dashboard', 'inventario'],
            'CLIENTE': [],
        }
        
        apps_permitidas = permisos_por_rol.get(self.id_rol.nombre_rol if self.id_rol else '', [])
        return app_label in apps_permitidas

    def get_all_permissions(self, obj=None):
        return set()
    
    def get_group_permissions(self, obj=None):
        return set()
    
    # =====================================================================
    # MÉTODOS ADICIONALES
    # =====================================================================
    
    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}"
    
    def get_short_name(self):
        return self.nombres
    
    def get_nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"
    
    def has_role(self, role_name):
        if self.id_rol:
            return self.id_rol.nombre_rol == role_name
        return False
    
    def has_any_role(self, role_names):
        if self.id_rol:
            return self.id_rol.nombre_rol in role_names
        return False
    
    def puede_eliminarse(self):
        """Verifica si el usuario puede eliminarse"""
        if self.id_rol and self.id_rol.nombre_rol == 'GERENTE':
            if Usuarios.objects.filter(
                id_rol__nombre_rol='GERENTE',
                deleted_at__isnull=True
            ).count() <= 1:
                return False
        return True

    def activar(self):
        """Activa el usuario"""
        self.estado = 'ACTIVO'
        self.deleted_at = None
        self.save()

    def desactivar(self):
        """Desactiva el usuario"""
        self.estado = 'INACTIVO'
        self.save()

    def suspender(self):
        """Suspende el usuario"""
        self.estado = 'SUSPENDIDO'
        self.save()

    def __str__(self):
        estado_icon = "✓" if self.is_active else "✗"
        return f"{estado_icon} {self.get_full_name()} ({self.correo_usuario})"