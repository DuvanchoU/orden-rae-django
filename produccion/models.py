from django.db import models

class Produccion(models.Model):
    id_produccion = models.AutoField(primary_key=True)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad_producida = models.IntegerField()
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_produccion = models.CharField(max_length=10)
    proveedor = models.ForeignKey('inventario.Proveedores', models.DO_NOTHING, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'produccion'


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