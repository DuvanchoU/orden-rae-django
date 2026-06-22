import pytest
from datetime import date
from decimal import Decimal


@pytest.mark.django_db
class TestIntegracionCompras:
    """Pruebas de integración: Compras + Inventario + Proveedores"""
    
    def test_flujo_completo_compra(self, usuario_admin, producto, proveedor):
        """Integración: Crear compra → Agregar productos → Recibir"""
        from compras.models import Compras
        
        # 1. Crear compra
        compra = Compras.objects.create(
            proveedor=proveedor,
            fecha_compra=date.today(),
            estado='PENDIENTE',
            usuario=usuario_admin
        )
        
        assert compra.estado == 'PENDIENTE'
        assert compra.proveedor == proveedor
        
        # 2. Agregar productos
        detalle = compra.agregar_producto(producto, cantidad=5, precio_unitario=Decimal('500000'))
        
        assert detalle.cantidad == 5
        assert detalle.subtotal == Decimal('2500000')
        
        # 3. Verificar total calculado (sin usar deleted_at)
        compra.calcular_total()
        assert compra.total_compra == Decimal('2500000')
        
        # 4. Recibir compra
        compra.recibir_compra()
        
        assert compra.estado == 'RECIBIDA'
    
    def test_compra_no_se_puede_modificar_si_recibida(self, usuario_admin, producto, proveedor):
        """Integración: Compra recibida → No se puede modificar"""
        from compras.models import Compras
        
        compra = Compras.objects.create(
            proveedor=proveedor,
            fecha_compra=date.today(),
            estado='RECIBIDA',
            usuario=usuario_admin
        )
        
        with pytest.raises(Exception):
            compra.agregar_producto(producto, cantidad=1, precio_unitario=Decimal('100000'))
    
    def test_compra_cancelada_no_afecta_inventario(self, usuario_admin, producto, proveedor):
        """Integración: Compra cancelada → No actualiza inventario"""
        from compras.models import Compras
        
        stock_inicial = producto.get_stock_total()
        
        compra = Compras.objects.create(
            proveedor=proveedor,
            fecha_compra=date.today(),
            estado='PENDIENTE',
            usuario=usuario_admin
        )
        
        compra.agregar_producto(producto, cantidad=5, precio_unitario=Decimal('500000'))
        compra.cancelar_compra()
        
        producto.refresh_from_db()
        assert producto.get_stock_total() == stock_inicial
        assert compra.estado == 'CANCELADA'