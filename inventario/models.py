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
    estado = models.CharField(max_length=8, blank=True, default='ACTIVA') 
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
    estado_categoria = models.CharField(max_length=45, blank=True, default='activo')
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

    def delete(self, using=None, keep_parents=False):
        """
        SOFT DELETE: En lugar de eliminar, marca deleted_at
        """
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self):
        """
        Eliminación real (solo si realmente se necesita borrar)
        """
        super().delete()

    def __str__(self):
        return self.nombre_categoria
    
class Proveedores(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    estado = models.CharField(max_length=8, blank=True, default='ACTIVO')
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'proveedores'
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    # AGREGAR SOFT DELETE 
    def delete(self, using=None, keep_parents=False):
        """
        SOFT DELETE: En lugar de eliminar, marca deleted_at
        """
        self.deleted_at = timezone.now()
        self.save()
    
    def hard_delete(self):
        """
        Eliminación real (solo si es necesario)
        """
        super().delete()
    
    # MÉTODOS DE NEGOCIO 
    def esta_activo(self):
        """Verifica si el proveedor está activo"""
        return self.estado == 'ACTIVO' and self.deleted_at is None
    
    def get_contacto_completo(self):
        """Retorna información completa de contacto"""
        contacto = f"{self.nombre}"
        if self.telefono:
            contacto += f" | Tel: {self.telefono}"
        if self.email:
            contacto += f" | {self.email}"
        return contacto

    def tiene_pedidos_asociados(self):
        """
        Verifica si el proveedor tiene pedidos asociados
        (Ajusta según tu modelo de Pedidos/Compras)
        """
        from compras.models import Compras
        return Compras.objects.filter(proveedor=self, deleted_at__isnull=True).exists()

    def __str__(self):
        estado = "✓" if self.esta_activo() else "✗"
        return f"{estado} {self.nombre}"

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
        related_name='productos',
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

    def get_imagen_principal(self):
        """Retorna la imagen principal del producto"""
        return ImagenesProducto.objects.filter(
            producto=self, 
            es_principal=1
        ).first()

    def get_stock_total(self):
        """Retorna el stock total sumando todas las bodegas"""
        inventarios = Inventario.objects.filter(
            producto=self,
            deleted_at__isnull=True
        )
        return sum(inv.cantidad_disponible for inv in inventarios)

    def esta_disponible(self):
        """Verifica si el producto está disponible"""
        return self.estado == 'DISPONIBLE' and self.get_stock_total() > 0

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
        on_delete=models.PROTECT, # CAMBIO IMPORTANTE: No dejar borrar un producto si tiene inventario
        db_column='producto_id', 
        to_field='id_producto',
        related_name='inventarios'
    )
    bodega = models.ForeignKey(
        Bodegas, 
        on_delete=models.PROTECT, 
        db_column='bodega_id',
        to_field='id_bodega',
        related_name='inventarios'
    )
    proveedor = models.ForeignKey(
        'Proveedores', 
        on_delete=models.SET_NULL, # Si borran el proveedor, queda null pero no se borra el inventario
        db_column='proveedor_id',
        to_field='id_proveedor',
        blank=True, 
        null=True,
        related_name='inventarios'
    )
    
    cantidad_disponible = models.IntegerField(default=0)
    cantidad_reservada = models.IntegerField(default=0, help_text="Cantidad reservada para pedidos pendientes")
    fecha_llegada = models.DateField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True) 
    estado = models.CharField(max_length=12, default='DISPONIBLE', choices=[
        ('DISPONIBLE', 'Disponible'),
        ('COMPROMETIDO', 'Comprometido'),
        ('AGOTADO', 'Agotado')
    ])
    
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventario'
        ordering = ['-fecha_registro']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Forzar 0 si es None inmediatamente al cargar el objeto
        if self.cantidad_reservada is None:
            self.cantidad_reservada = 0

    def clean(self):
        # Validación 1: Stock no negativo
        if self.cantidad_disponible < 0:
            raise ValidationError("La cantidad disponible no puede ser negativa.")
        
        # Validación 2: Cantidad reservada no puede ser mayor a la disponible
        if self.cantidad_reservada > self.cantidad_disponible:
            raise ValidationError("La cantidad reservada no puede ser mayor a la disponible.")

        # Validación 3: Estado coherente con cantidad
        if self.cantidad_disponible == 0 and self.estado != 'AGOTADO':
            # Advertencia o forzamos estado (depende de tu política). Aquí solo validamos lógica.
            pass 
        
        # Validación 4: Producto y Bodega no deben estar eliminados
        if self.producto.deleted_at:
            raise ValidationError("No se puede asociar inventario a un producto eliminado.")
        if self.bodega.deleted_at:
            raise ValidationError("No se puede asociar inventario a una bodega eliminada.")
        
    def save(self, *args, **kwargs):
        # Auto-fechas
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()

        # Ejecutar validaciones antes de guardar
        self.full_clean()

        # Lógica automática de estado considerando lo reservado
        stock_real = self.cantidad_disponible - self.cantidad_reservada
        
        if stock_real <= 0:
            self.estado = 'AGOTADO' 
        elif self.cantidad_reservada > 0:
            self.estado = 'COMPROMETIDO'
        else:
            self.estado = 'DISPONIBLE'

        super().save(*args, **kwargs)

    def agregar_stock(self, cantidad, proveedor=None, fecha=None):
        """Método seguro para aumentar stock"""
        if cantidad <= 0:
            raise ValidationError("La cantidad a agregar debe ser positiva.")
        self.cantidad_disponible += cantidad
        if proveedor:
            self.proveedor = proveedor
        if fecha:
            self.fecha_llegada = fecha
        self.save()

    def retirar_stock(self, cantidad):
        """Método seguro para disminuir stock"""
        if cantidad <= 0:
            raise ValidationError("La cantidad a retirar debe ser positiva.")
        if self.cantidad_disponible < cantidad:
            raise ValidationError(f"Stock insuficiente. Disponible: {self.cantidad_disponible}")
        
        self.cantidad_disponible -= cantidad
        self.save()

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()

    def __str__(self):
        return f"{self.producto.codigo_producto} ({self.cantidad_disponible}) en {self.bodega.nombre_bodega}"

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