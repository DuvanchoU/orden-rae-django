from django.db import models

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


class MetodosPago(models.Model):
    id_metodo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'metodos_pago'

    def __str__(self):
            return self.nombre


class Carritos(models.Model):
    id_carrito = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING, blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'carritos'

    def __str__(self):
        if self.cliente:
            return f"Carrito #{self.id_carrito} - {self.cliente}"
        return f"Carrito #{self.id_carrito} (Sin cliente)"
    

class ItemsCarrito(models.Model):
    id_item = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carritos, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING) 
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'items_carrito'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"


class Cotizaciones(models.Model):
    id_cotizacion = models.AutoField(primary_key=True)
    numero_cotizacion = models.CharField(unique=True, max_length=255)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING) 
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
        managed = True
        db_table = 'cotizaciones'

    def __str__(self):
        return f"Cotización #{self.numero_cotizacion} - {self.cliente}"
    
    def subtotal_formateado(self):
        """
        Retorna el subtotal formateado sin decimales y con separador de miles
        Ejemplo: 1199998 → $1.199.998
        """
        return f"{int(self.subtotal):,}".replace(",", ".")
    
    def impuesto_formateado(self):
        """
        Retorna el impuesto formateado sin decimales y con separador de miles
        Ejemplo: 228000 → $228.000
        """
        return f"{int(self.impuesto):,}".replace(",", ".")
    
    def descuento_formateado(self):
        """
        Retorna el descuento formateado sin decimales y con separador de miles
        Ejemplo: 50000 → $50.000
        """
        if self.descuento:
            return f"{int(self.descuento):,}".replace(",", ".")
        return "$0"
    
    def total_formateado(self):
        """
        Retorna el total formateado sin decimales y con separador de miles
        Ejemplo: 1427998 → $1.427.998
        """
        return f"{int(self.total):,}".replace(",", ".")
    
class DetalleCotizacion(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    cotizacion = models.ForeignKey(Cotizaciones, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
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
        managed = True
        db_table = 'detalle_cotizacion'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"
    
    def precio_unitario_formateado(self):
        """
        Retorna el precio unitario formateado sin decimales y con separador de miles
        """
        return f"{int(self.precio_unitario):,}".replace(",", ".")
    
    def subtotal_formateado(self):
        """
        Retorna el subtotal formateado sin decimales y con separador de miles
        """
        return f"{int(self.subtotal):,}".replace(",", ".")
    
    def descuento_formateado(self):
        """
        Retorna el descuento formateado sin decimales y con separador de miles
        """
        if self.descuento:
            return f"{int(self.descuento):,}".replace(",", ".")
        return "$0"
    

class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING)
    cliente = models.ForeignKey(Clientes, models.DO_NOTHING)
    fecha_pedido = models.DateTimeField()
    fecha_entrega_estimada = models.DateField(blank=True, null=True)
    total_pedido = models.DecimalField(max_digits=15, decimal_places=2)
    estado_pedido = models.CharField(max_length=10)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    asesor = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, related_name='pedido_asesor_set', blank=True, null=True)
    numero_pedido = models.CharField(unique=True, max_length=255, blank=True, null=True)
    foto_orden = models.CharField(max_length=255, blank=True, null=True)
    estado_facturacion = models.CharField(max_length=12, blank=True, null=True)
    fecha_facturacion = models.DateTimeField(blank=True, null=True)
    usuario_facturo = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING, related_name='pedido_usuario_facturo_set', blank=True, null=True)

    def precio_formateado(self):
        """
        Retorna el precio formateado sin decimales y con separador de miles
        Ejemplo: 950000 → $950.000
        """
        return f"{int(self.total_pedido):,}".replace(",", ".")
    
    def __str__(self):
        numero = self.numero_pedido or f"#{self.id_pedido}"
        return f"Pedido {numero} - {self.cliente}"
    
    class Meta:
        managed = True
        db_table = 'pedido'


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
        managed = True
        db_table = 'detalle_pedido'

    def __str__(self):
        # Nota: Este modelo usa IDs en lugar de FKs, así que no podemos acceder al nombre del producto directamente
        return f"Detalle #{self.id_detalle} - Producto ID: {self.producto_id}"
    

class Ventas(models.Model):
    id_venta = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuarios', models.DO_NOTHING)
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
        managed = True
        db_table = 'ventas'

    def precio_formateado(self):
        """
        Retorna el precio formateado sin decimales y con separador de miles
        Ejemplo: 950000 → $950.000
        """
        return f"{int(self.total):,}".replace(",", ".")
    
    def __str__(self):
        cliente_name = self.cliente.nombre if self.cliente else "Sin cliente"
        return f"Venta #{self.id_venta} - {cliente_name}"
    

class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Ventas, models.DO_NOTHING)
    producto = models.ForeignKey('inventario.Producto', models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'detalle_venta'

    def __str__(self):
        return f"{self.producto} x{self.cantidad}"