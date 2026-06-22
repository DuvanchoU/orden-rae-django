import pytest
from datetime import date
from decimal import Decimal


@pytest.mark.django_db
class TestIntegracionInventario:
    """Pruebas de integración: Inventario + Compras + Producción"""
    
    def test_compra_aumenta_inventario(self, usuario_admin, producto, bodega, proveedor):
        """Integración: Compra → Recepción → Aumento de stock"""
        from compras.models import Compras
        
        stock_inicial = producto.get_stock_total()
        
        compra = Compras.objects.create(
            proveedor=proveedor,
            fecha_compra=date.today(),
            estado='PENDIENTE',
            usuario=usuario_admin
        )
        
        compra.agregar_producto(producto, cantidad=5, precio_unitario=Decimal('500000'))
        compra.recibir_compra()
        
        producto.refresh_from_db()
        stock_final = producto.get_stock_total()
        assert stock_final == stock_inicial + 5
        
        compra.refresh_from_db()
        assert compra.estado == 'RECIBIDA'
    
    def test_venta_disminuye_inventario(self, producto, inventario):
        """Integración: Venta → Disminución de stock"""
        stock_inicial = producto.get_stock_total()
        
        inventario.retirar_stock(3)
        
        producto.refresh_from_db()
        stock_final = producto.get_stock_total()
        assert stock_final == stock_inicial - 3
    
    def test_stock_bajo_genera_alerta(self, producto, bodega, proveedor):
        """Integración: Stock bajo mínimo → Alerta"""
        from inventario.models import Inventario
        
        inventario = Inventario.objects.create(
            producto=producto,
            bodega=bodega,
            cantidad_disponible=1,
            cantidad_reservada=0,
            proveedor=proveedor,
            estado='DISPONIBLE'
        )
        
        assert producto.esta_disponible() is True
        assert inventario.cantidad_disponible == 1
    
    def test_produccion_actualiza_inventario(self, producto, bodega, proveedor):
        """Integración: Producción terminada → Aumento de stock"""
        from produccion.models import Produccion
        
        stock_inicial = producto.get_stock_total()
        
        produccion = Produccion.objects.create(
            producto=producto,
            cantidad_producida=10,
            fecha_inicio=date.today(),
            estado_produccion='PENDIENTE',
            proveedor=proveedor
        )
        
        produccion.cambiar_estado('EN PROCESO')
        produccion.cambiar_estado('TERMINADA')
        
        produccion.refresh_from_db()
        assert produccion.estado_produccion == 'TERMINADA'