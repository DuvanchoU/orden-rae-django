import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone


@pytest.mark.django_db
class TestIntegracionPedidos:
    """Pruebas de integración: Pedidos + Producción + Inventario"""
    
    def test_flujo_pedido_completo(self, usuario_asesor, cliente, producto, inventario):
        """Integración: Crear pedido → Confirmar → En proceso → Completado"""
        from ventas.models import Pedido, DetallePedido
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            asesor=usuario_asesor,
            fecha_pedido=timezone.now(),
            fecha_entrega_estimada=date.today() + timedelta(days=7),
            estado_pedido='PENDIENTE',
            direccion_entrega='Calle 123 #45-67',
            total_pedido=Decimal('0')
        )
        
        assert pedido.estado_pedido == 'PENDIENTE'
        
        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=3,
            precio_unitario=Decimal('800000')
        )
        
        pedido.calcular_total()
        
        assert pedido.total_pedido == Decimal('2400000')
        
        pedido.cambiar_estado('CONFIRMADO')
        assert pedido.estado_pedido == 'CONFIRMADO'
        
        pedido.cambiar_estado('EN PROCESO')
        assert pedido.estado_pedido == 'EN PROCESO'
        
        pedido.cambiar_estado('COMPLETADO')
        assert pedido.estado_pedido == 'COMPLETADO'
        
        assert pedido.puede_facturarse() is True
    
    def test_pedido_con_produccion(self, usuario_asesor, cliente, producto):
        """Integración: Pedido → Requiere producción"""
        from ventas.models import Pedido, DetallePedido
        from produccion.models import Produccion
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            asesor=usuario_asesor,
            fecha_pedido=timezone.now(),
            fecha_entrega_estimada=date.today() + timedelta(days=15),
            estado_pedido='PENDIENTE',
            total_pedido=Decimal('0')
        )
        
        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=5,
            precio_unitario=Decimal('800000')
        )
        
        pedido.calcular_total()
        
        produccion = Produccion.objects.create(
            producto=producto,
            cantidad_producida=5,
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=10),
            estado_produccion='PENDIENTE'
        )
        
        assert produccion.estado_produccion == 'PENDIENTE'
        assert produccion.cantidad_producida == 5
        
        produccion.cambiar_estado('EN PROCESO')
        produccion.cambiar_estado('TERMINADA')
        
        assert produccion.estado_produccion == 'TERMINADA'
        assert produccion.fecha_fin is not None
    
    def test_pedido_cancelado_no_afecta_inventario(self, cliente, producto, inventario):
        """Integración: Pedido cancelado → No afecta inventario"""
        from ventas.models import Pedido, DetallePedido
        
        stock_inicial = inventario.cantidad_disponible
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            fecha_pedido=timezone.now(),
            estado_pedido='PENDIENTE',
            total_pedido=Decimal('0')
        )
        
        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal('800000')
        )
        
        pedido.calcular_total()
        pedido.cambiar_estado('CANCELADO')
        
        inventario.refresh_from_db()
        assert inventario.cantidad_disponible == stock_inicial
        assert pedido.estado_pedido == 'CANCELADO'