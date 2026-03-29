from django.db import models
from django.db.models import Sum 
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction

class Produccion(models.Model):
    ESTADOS_PRODUCCION = [
        ('PENDIENTE', 'Pendiente'),
        ('EN PROCESO', 'En Proceso'),
        ('TERMINADA', 'Terminada'),
        ('CANCELADA', 'Cancelada'),
    ]

    id_produccion = models.AutoField(primary_key=True)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad_producida = models.IntegerField()
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_produccion = models.CharField(
        max_length=15,
        choices=ESTADOS_PRODUCCION,
        default='PENDIENTE'
    )
    proveedor = models.ForeignKey(
        'inventario.Proveedores', 
        models.DO_NOTHING, 
        blank=True, 
        null=True
    )
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'produccion'
        ordering = ['-fecha_inicio', '-created_at']
    
    def clean(self):
        """Validaciones del modelo"""
        if self.cantidad_producida and self.cantidad_producida <= 0:
            raise ValidationError("La cantidad producida debe ser mayor a 0")
        
        # Fecha fin no puede ser menor que fecha inicio
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                raise ValidationError("La fecha de fin no puede ser anterior a la fecha de inicio")
        
         # Validar duplicados (creación y edición)
        if self.fecha_inicio:
            duplicados = Produccion.objects.filter(
                producto=self.producto,
                fecha_inicio=self.fecha_inicio,
                estado_produccion__in=['PENDIENTE', 'EN PROCESO'],
                deleted_at__isnull=True
            )
            if self.pk:
                duplicados = duplicados.exclude(pk=self.pk)
                
            if duplicados.exists():
                raise ValidationError("Ya existe una producción activa para este producto en esta fecha")

    def save(self, *args, **kwargs):
        """Auto-gestión de timestamps"""
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.save()
        return self

    def hard_delete(self):
        """Eliminación física real"""
        super().delete()

    def puede_modificarse(self):
        """Verifica si la producción puede ser modificada"""
        return self.estado_produccion not in ['TERMINADA', 'CANCELADA']

    def puede_eliminarse(self):
        """Verifica si puede eliminarse"""
        return self.estado_produccion == 'PENDIENTE' and not self.detalleproduccionpedido_set.exists()

    def get_cantidad_asignada(self):
        """Obtiene la cantidad total asignada a pedidos"""
        total = self.detalleproduccionpedido_set.filter(
            deleted_at__isnull=True
        ).aggregate(
            total=Sum('cantidad_asignada')
        )['total'] or 0
        return float(total)

    def get_cantidad_disponible(self):
        """Cantidad producida menos la asignada"""
        return self.cantidad_producida - self.get_cantidad_asignada()

    def esta_completamente_asignada(self):
        """Verifica si toda la producción está asignada"""
        return self.get_cantidad_asignada() >= self.cantidad_producida

    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado con validaciones"""
        if not self.puede_modificarse():
            raise ValidationError(f"No se puede modificar una producción {self.estado_produccion}")
        
        estados_validos = {
            'PENDIENTE': ['EN PROCESO', 'CANCELADA'],
            'EN PROCESO': ['TERMINADA', 'CANCELADA'],
            'TERMINADA': [],
            'CANCELADA': []
        }
        
        if nuevo_estado not in estados_validos.get(self.estado_produccion, []):
            raise ValidationError(
                f"No se puede cambiar de {self.estado_produccion} a {nuevo_estado}"
            )
        
        self.estado_produccion = nuevo_estado
        if nuevo_estado == 'TERMINADA' and not self.fecha_fin:
            self.fecha_fin = timezone.now().date()
        self.save()

    def __str__(self):
        return f"{self.producto.codigo_producto} - {self.cantidad_producida} und ({self.estado_produccion})"


class DetalleProduccionPedido(models.Model):
    id = models.BigAutoField(primary_key=True)
    produccion = models.ForeignKey('Produccion', models.DO_NOTHING)
    pedido = models.ForeignKey('ventas.Pedido', models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_produccion_pedido'
        unique_together = (('produccion', 'pedido', 'producto'),)

    def clean(self):
        if self.cantidad_asignada and self.cantidad_asignada <= 0:
            raise ValidationError("La cantidad asignada debe ser mayor a 0")
        
        # Validar que no exceda la cantidad disponible de producción
        if self.produccion and self.cantidad_asignada:
            disponible = self.produccion.get_cantidad_disponible()
            # Si es actualización, restar la cantidad anterior
            if self.pk:
                try:
                    original = DetalleProduccionPedido.objects.get(pk=self.pk)
                    disponible += float(original.cantidad_asignada)
                except DetalleProduccionPedido.DoesNotExist:
                    pass
            
            if float(self.cantidad_asignada) > disponible:
                raise ValidationError(
                    f"La cantidad asignada ({self.cantidad_asignada}) excede la disponible ({disponible})"
                )

    def save(self, *args, **kwargs):
        if not self.pk and not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft delete"""
        self.deleted_at = timezone.now()
        self.save()
        return self

    def __str__(self):
        return f"{self.produccion} -> Pedido {self.pedido.id} ({self.cantidad_asignada})"