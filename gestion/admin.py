from django.contrib import admin
from .models import (
    Bodegas, Carritos, Categorias, Clientes, Compras, Cotizaciones,
    DetalleCompra, DetalleCompraPedido, DetalleCotizacion, DetallePedido,
    DetalleProduccionPedido, DetalleVenta, ImagenesProducto, Inventario,
    ItemsCarrito, MetodosPago, Pedido, Produccion, Producto, Proveedores,
    RolesOld, Usuarios, Ventas
)

# Registramos TODAS las tablas para que aparezcan en el admin
admin.site.register(Bodegas)
admin.site.register(Carritos)
admin.site.register(Categorias)
admin.site.register(Clientes)
admin.site.register(Compras)
admin.site.register(Cotizaciones)
admin.site.register(DetalleCompra)
admin.site.register(DetalleCompraPedido)
admin.site.register(DetalleCotizacion)
admin.site.register(DetallePedido)
admin.site.register(DetalleProduccionPedido)
admin.site.register(DetalleVenta)
admin.site.register(ImagenesProducto)
admin.site.register(Inventario)
admin.site.register(ItemsCarrito)
admin.site.register(MetodosPago)
admin.site.register(Pedido)
admin.site.register(Produccion)
admin.site.register(Producto)
admin.site.register(Proveedores)
admin.site.register(RolesOld)
admin.site.register(Ventas)

# Registro personalizado para Usuarios para que se vea bonito
@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'nombres', 'apellidos', 'correo_usuario', 'estado')
    search_fields = ('nombres', 'documento', 'correo_usuario')
    list_filter = ('estado', 'id_rol')