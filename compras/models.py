from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, F
from django.db import transaction
from decimal import Decimal

class Compras(models.Model):
    ESTADOS_COMPRA = [
        ('PENDIENTE', 'Pendiente'),
        ('RECIBIDA', 'Recibida'),
        ('CANCELADA', 'Cancelada'),
    ]

    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey('inventario.Proveedores', models.DO_NOTHING)
    fecha_compra = models.DateField()
    total_compra = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=10,
        choices=ESTADOS_COMPRA,
        default='PENDIENTE',
        blank=True, 
        null=True
    )
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'compras'
        ordering = ['-fecha_compra', '-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['proveedor']),
            models.Index(fields=['fecha_compra']),
        ]

    def __str__(self):
        return f"Compra #{self.id_compra} - {self.proveedor.nombre}"
    
    def clean(self):
        """Validaciones del modelo"""
        if self.total_compra < 0:
            raise ValidationError("El total de la compra no puede ser negativo")
        
        if self.fecha_compra and self.fecha_compra > timezone.now().date():
            raise ValidationError("La fecha de compra no puede ser futura")

    def save(self, *args, **kwargs):
        """Auto-gestión de timestamps"""
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
            if not self.fecha_compra:
                self.fecha_compra = timezone.now().date()
        
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete - solo si está pendiente"""
        if self.estado != 'PENDIENTE':
            raise ValidationError(f"No se puede eliminar una compra en estado {self.estado}")
        self.deleted_at = timezone.now()
        self.save()
        return self

    def hard_delete(self):
        """Eliminación física solo si no tiene detalles"""
        if self.detallecompra_set.exists():
            raise ValidationError("No se puede eliminar permanentemente una compra con productos")
        super().delete()

    def puede_modificarse(self):
        """Verifica si la compra puede ser modificada"""
        return self.estado == 'PENDIENTE'

    def puede_eliminarse(self):
        """Verifica si puede eliminarse"""
        return self.estado == 'PENDIENTE'

    def puede_recibirse(self):
        """Verifica si puede marcarse como recibida"""
        return self.estado == 'PENDIENTE' and self.detallecompra_set.exists()

    def calcular_total(self):
        """Calcula el total desde los detalles"""
        detalles = self.detallecompra_set.filter(deleted_at__isnull=True)
        total = sum(d.subtotal for d in detalles)
        self.total_compra = total
        self.save()
        return total

    def agregar_producto(self, producto, cantidad, precio_unitario):
        """Agrega un producto a la compra"""
        if not self.puede_modificarse():
            raise ValidationError(f"No se puede modificar una compra {self.estado}")
        
        from inventario.models import Producto
        if producto.estado != 'DISPONIBLE':
            raise ValidationError(f"El producto {producto.codigo_producto} no está disponible")
        
        detalle, created = DetalleCompra.objects.get_or_create(
            compra=self,
            producto=producto,
            defaults={
                'cantidad': cantidad,
                'precio_unitario': precio_unitario,
            }
        )
        
        if not created:
            detalle.cantidad += cantidad
            detalle.precio_unitario = precio_unitario
            detalle.save()
        
        self.calcular_total()
        return detalle

    def recibir_compra(self):
        """Marca la compra como recibida y actualiza inventario"""
        if not self.puede_recibirse():
            raise ValidationError("La compra no puede ser recibida")
        
        with transaction.atomic():
            self.estado = 'RECIBIDA'
            self.save()
            
            # Actualizar inventario
            for detalle in self.detallecompra_set.all():
                detalle.actualizar_inventario()

    def cancelar_compra(self):
        """Cancela la compra"""
        if self.estado != 'PENDIENTE':
            raise ValidationError(f"No se puede cancelar una compra {self.estado}")
        
        self.estado = 'CANCELADA'
        self.save()
    
    def get_total_formateado(self):
        """Retorna el total formateado"""
        return f"${int(self.total_compra):,}".replace(",", ".")

    def get_cantidad_productos(self):
        """Obtiene la cantidad total de productos"""
        return self.detallecompra_set.aggregate(
            total=Sum('cantidad')
        )['total'] or 0

    def __str__(self):
        return f"Compra #{self.id_compra} - {self.proveedor.nombre} ({self.estado})"
    

class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compras, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        managed = True
        db_table = 'detalle_compra'
        indexes = [
            models.Index(fields=['compra']),
            models.Index(fields=['producto']),
        ]
    
    def clean(self):
        """Validaciones del detalle"""
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        if self.precio_unitario < 0:
            raise ValidationError("El precio unitario no puede ser negativo")
        if self.subtotal < 0:
            raise ValidationError("El subtotal no puede ser negativo")

    def save(self, *args, **kwargs):
        """Auto-calcular subtotal"""
        if not self.pk:
            self.created_at = timezone.now()
        
        self.updated_at = timezone.now()
        
        # Calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Recalcular total de la compra
        if self.compra:
            self.compra.calcular_total()

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.save()
        return self

    def actualizar_inventario(self):
        """Actualiza el inventario al recibir la compra"""
        from inventario.models import Inventario
        
        # Buscar o crear registro de inventario
        inventario, created = Inventario.objects.get_or_create(
            producto=self.producto,
            bodega_id=1,  # Ajustar según tu lógica de bodegas
            defaults={
                'cantidad_disponible': 0,
                'proveedor_id': self.compra.proveedor_id,
            }
        )
        
        # Actualizar cantidad
        inventario.cantidad_disponible += self.cantidad
        inventario.fecha_llegada = self.compra.fecha_compra
        inventario.estado = 'DISPONIBLE'
        inventario.save()

    def get_subtotal_formateado(self):
        """Retorna el subtotal formateado"""
        return f"${int(self.subtotal):,}".replace(",", ".")

    def get_precio_unitario_formateado(self):
        """Retorna el precio unitario formateado"""
        return f"${int(self.precio_unitario):,}".replace(",", ".")

    def __str__(self):
        return f"{self.producto.codigo_producto} x{self.cantidad}"


class DetalleCompraPedido(models.Model):
    compra = models.ForeignKey(Compras, models.DO_NOTHING)
    pedido = models.ForeignKey('ventas.Pedido', models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_compra_pedido'
        unique_together = (('compra', 'pedido', 'producto'),)

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()
        return self

