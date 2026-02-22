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

    class Meta:
        managed = True
        db_table = 'usuarios'