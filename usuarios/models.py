from django.db import models

class RolesOld(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(unique=True, max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'roles_old'


class Usuarios(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    documento = models.CharField(unique=True, max_length=20)
    correo_usuario = models.CharField(unique=True, max_length=255)
    contrasena_usuario = models.CharField(max_length=255)
    genero = models.CharField(max_length=1, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    estado = models.CharField(max_length=8)
    fecha_registro = models.DateTimeField()
    id_rol = models.ForeignKey(RolesOld, models.DO_NOTHING, db_column='id_rol')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    # =====================================================================
    # PROPIEDADES PARA COMPATIBILIDAD CON DJANGO
    # =====================================================================
    
    @property
    def username(self):
        return self.correo_usuario
    
    """Compatibilidad: retorna correo_usuario como email"""
    @property
    def email(self):
        return self.correo_usuario
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return self.estado == 'ACTIVO'
    
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
    # MÉTODOS DE PERMISOS PARA DJANGO ADMIN
    # =====================================================================
    
    def has_perm(self, perm, obj=None):
        """Verifica si el usuario tiene un permiso específico"""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return True  # Personaliza según necesites
    
    def has_module_perms(self, app_label):
        """Verifica si el usuario tiene permisos para una app del admin"""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        
        # Mapeo de apps permitidas por rol
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
        """Retorna todos los permisos del usuario"""
        if not self.is_active:
            return set()
        return set()
    
    def get_group_permissions(self, obj=None):
        """Retorna permisos de grupos"""
        return set()
    
    # =====================================================================
    # MÉTODOS ADICIONALES ÚTILES
    # =====================================================================
    
    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}"
    
    def get_short_name(self):
        return self.nombres
    
    def has_role(self, role_name):
        if self.id_rol:
            return self.id_rol.nombre_rol == role_name
        return False
    
    def has_any_role(self, role_names):
        if self.id_rol:
            return self.id_rol.nombre_rol in role_names
        return False

    class Meta:
        managed = True
        db_table = 'usuarios'