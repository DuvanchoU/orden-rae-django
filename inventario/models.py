from django.db import models

class Bodegas(models.Model):
    id_bodega = models.AutoField(primary_key=True)
    nombre_bodega = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=8, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'bodegas'


class Categorias(models.Model):
    id_categorias = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=300)
    estado_categoria = models.CharField(max_length=45, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria
    
    class Meta:
        managed = True
        db_table = 'categorias'


class Proveedores(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=8, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'proveedores'


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    codigo_producto = models.CharField(max_length=45)
    referencia_producto = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.ForeignKey(Categorias, models.DO_NOTHING)
    proveedor_id = models.PositiveIntegerField(blank=True, null=True)
    tipo_madera = models.CharField(max_length=45, blank=True, null=True)
    color_producto = models.CharField(max_length=45, blank=True, null=True)
    precio_actual = models.DecimalField(max_digits=15, decimal_places=2)
    estado = models.CharField(max_length=10)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    def precio_formateado(self):
        """
        Retorna el precio formateado sin decimales y con separador de miles
        Ejemplo: 950000 → $950.000
        """
        return f"{int(self.precio_actual):,}".replace(",", ".")
    
    def __str__(self):
        return f"{self.codigo_producto} - {self.referencia_producto}"
    
    class Meta:
        managed = True
        db_table = 'producto'


class Inventario(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    bodega = models.ForeignKey(Bodegas, models.DO_NOTHING)
    proveedor = models.ForeignKey('Proveedores', models.DO_NOTHING, blank=True, null=True)
    cantidad_disponible = models.IntegerField()
    fecha_llegada = models.DateField(blank=True, null=True)
    fecha_registro = models.DateTimeField()
    estado = models.CharField(max_length=12)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'inventario'


class ImagenesProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    ruta_imagen = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    es_principal = models.IntegerField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'imagenes_producto'