# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
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
        managed = False
        db_table = 'bodegas'


class Carritos(models.Model):
    id_carrito = models.AutoField(primary_key=True)
    cliente = models.ForeignKey('Clientes', models.DO_NOTHING, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'carritos'


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


class Clientes(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=8, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        if self.apellido:
            return f"{self.nombre} {self.apellido}"
        return self.nombre
    
    class Meta:
        managed = True
        db_table = 'clientes'


class Compras(models.Model):
    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey('Proveedores', models.DO_NOTHING)
    fecha_compra = models.DateField()
    total_compra = models.DecimalField(max_digits=15, decimal_places=2)
    estado = models.CharField(max_length=9, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'compras'


class Cotizaciones(models.Model):
    id_cotizacion = models.AutoField(primary_key=True)
    numero_cotizacion = models.CharField(unique=True, max_length=255)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    venta_id = models.IntegerField(blank=True, null=True)
    fecha_cotizacion = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=9)
    tiempo_entrega = models.CharField(max_length=255, blank=True, null=True)
    validez_dias = models.IntegerField(blank=True, null=True)
    moneda = models.CharField(max_length=10, blank=True, null=True)
    requiere_produccion = models.IntegerField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    impuesto = models.DecimalField(max_digits=15, decimal_places=2)
    descuento = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    consecutivo = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cotizaciones'


class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compras, models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'detalle_compra'


class DetalleCompraPedido(models.Model):
    compra = models.ForeignKey(Compras, models.DO_NOTHING)
    pedido = models.ForeignKey('Pedido', models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'detalle_compra_pedido'
        unique_together = (('compra', 'pedido', 'producto'),)


class DetalleCotizacion(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    cotizacion = models.ForeignKey(Cotizaciones, models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    descuento = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    costo_estimado = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'detalle_cotizacion'


class DetallePedido(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    pedido_id = models.IntegerField()
    producto_id = models.IntegerField()
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'detalle_pedido'


class DetalleProduccionPedido(models.Model):
    id = models.BigAutoField(primary_key=True)
    produccion = models.ForeignKey('Produccion', models.DO_NOTHING)
    pedido = models.ForeignKey('Pedido', models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad_asignada = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'detalle_produccion_pedido'
        unique_together = (('produccion', 'pedido', 'producto'),)


class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    venta = models.ForeignKey('Ventas', models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'detalle_venta'


class ImagenesProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    ruta_imagen = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    es_principal = models.IntegerField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'imagenes_producto'


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
        managed = False
        db_table = 'inventario'


class ItemsCarrito(models.Model):
    id_item = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carritos, models.DO_NOTHING)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'items_carrito'


class MetodosPago(models.Model):
    id_metodo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'metodos_pago'


class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING)
    fecha_pedido = models.DateTimeField()
    fecha_entrega_estimada = models.DateField(blank=True, null=True)
    total_pedido = models.DecimalField(max_digits=15, decimal_places=2)
    estado_pedido = models.CharField(max_length=10)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    asesor = models.ForeignKey('Usuarios', models.DO_NOTHING, related_name='pedido_asesor_set', blank=True, null=True)
    numero_pedido = models.CharField(unique=True, max_length=255, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    estado_facturacion = models.CharField(max_length=12, blank=True, null=True)
    fecha_facturacion = models.DateTimeField(blank=True, null=True)
    usuario_facturo = models.ForeignKey('Usuarios', models.DO_NOTHING, related_name='pedido_usuario_facturo_set', blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'pedido'


class Produccion(models.Model):
    id_produccion = models.AutoField(primary_key=True)
    producto = models.ForeignKey('Producto', models.DO_NOTHING)
    cantidad_producida = models.IntegerField()
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_produccion = models.CharField(max_length=10)
    proveedor = models.ForeignKey('Proveedores', models.DO_NOTHING, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'produccion'


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

    class Meta:
        managed = False
        db_table = 'producto'


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


class RolesOld(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(unique=True, max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
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
        managed = False
        db_table = 'usuarios'
        

class Ventas(models.Model):
    id_venta = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuarios, models.DO_NOTHING)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING, blank=True, null=True)
    pedido = models.OneToOneField(Pedido, models.DO_NOTHING, blank=True, null=True)
    tipo_venta = models.CharField(max_length=12)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    fecha_venta = models.DateTimeField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado_venta = models.CharField(max_length=10)
    metodo_pago = models.ForeignKey(MetodosPago, models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    numero_factura = models.CharField(max_length=50, blank=True, null=True)
    prefijo = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ventas'
