from django.db import models

class Compras(models.Model):
    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey('inventario.Proveedores', models.DO_NOTHING)
    fecha_compra = models.DateField()
    total_compra = models.DecimalField(max_digits=15, decimal_places=2)
    estado = models.CharField(max_length=9, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'compras'

    def __str__(self):
        return f"Compra #{self.id_compra} - {self.proveedor.nombre}"
    
    def total_formateado(self):
        """
        Retorna el total formateado sin decimales y con separador de miles
        Ejemplo: 1427998 → $1.427.998
        """
        return f"{int(self.total_compra):,}".replace(",", ".")
    

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

