from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# ------------------------------------------------------------------
# MODELOS CATÁLOGOS (Bodegas, Categorías, Proveedores)
# ------------------------------------------------------------------

class Bodegas(models.Model):
    id_bodega = models.AutoField(primary_key=True)
    nombre_bodega = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=8, blank=True, null=True) 
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bodegas'

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_bodega

class Categorias(models.Model):
    id_categorias = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=300)
    estado_categoria = models.CharField(max_length=45, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'categorias'
        ordering = ['nombre_categoria']

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_categoria
    
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
        managed = False
        db_table = 'proveedores'

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

# ------------------
# MODELO PRODUCTO
# ------------------

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    codigo_producto = models.CharField(max_length=45, unique=True)
    referencia_producto = models.CharField(max_length=100, blank=True, null=True)
    
    # Relación explícita a la columna categoria_id y llave primaria id_categorias
    categoria = models.ForeignKey(
        Categorias, 
        on_delete=models.DO_NOTHING, 
        db_column='categoria_id',
        to_field='id_categorias',
        related_name='productos' 
    )
    
    proveedor_id = models.PositiveIntegerField(blank=True, null=True)
    tipo_madera = models.CharField(max_length=45, blank=True, null=True)
    color_producto = models.CharField(max_length=45, blank=True, null=True)
    precio_actual = models.DecimalField(max_digits=15, decimal_places=2)
    
    estado = models.CharField(
        max_length=10,
        choices=[('DISPONIBLE', 'Disponible'), ('AGOTADO', 'Agotado')],
        default='DISPONIBLE'
    )
    
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    def clean(self):
        if self.precio_actual is not None and self.precio_actual <= 0:
            raise ValidationError("El precio debe ser mayor a cero.")
        if not self.codigo_producto or not self.codigo_producto.strip():
            raise ValidationError("El código del producto no puede estar vacío.")

    def save(self, *args, **kwargs):
        # Auto-fechas
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        
        # Ejecutar validaciones antes de guardar
        self.full_clean() 
        
        super().save(*args, **kwargs)

    def precio_formateado(self):
        """Retorna el precio formateado: $1.200.000"""
        if self.precio_actual is None:
            return ""
        return f"{int(self.precio_actual):,}".replace(",", ".")
    
    def is_deleted(self):
        return self.deleted_at is not None

    def restore(self):
        self.deleted_at = None
        self.save()

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.codigo_producto} - {self.referencia_producto or 'Sin referencia'}"
    
    class Meta:
        managed = False  
        db_table = 'producto'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['codigo_producto']),
            models.Index(fields=['estado']),
            models.Index(fields=['categoria']),
        ]

# ------------------------------------------------------------------
# MODELOS TRANSACCIONALES (Inventario, Imágenes)
# ------------------------------------------------------------------

class Inventario(models.Model):
    id_inventario = models.AutoField(primary_key=True)

    producto = models.ForeignKey(
        'Producto', 
        on_delete=models.DO_NOTHING, 
        db_column='producto_id', 
        to_field='id_producto'
    )
    bodega = models.ForeignKey(
        Bodegas, 
        on_delete=models.DO_NOTHING, 
        db_column='bodega_id',
        to_field='id_bodega'
    )
    proveedor = models.ForeignKey(
        'Proveedores', 
        on_delete=models.DO_NOTHING, 
        db_column='proveedor_id',
        to_field='id_proveedor',
        blank=True, 
        null=True
    )
    
    cantidad_disponible = models.IntegerField(default=0)
    fecha_llegada = models.DateField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True) 
    estado = models.CharField(max_length=12, default='DISPONIBLE')
    
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventario'

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.codigo_producto} en {self.bodega.nombre_bodega}"

class ImagenesProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        'Producto', 
        on_delete=models.DO_NOTHING, 
        db_column='producto_id',
        to_field='id_producto'
    )
    ruta_imagen = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    es_principal = models.IntegerField(default=0) 
    
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'imagenes_producto'

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagen de {self.producto.codigo_producto}"