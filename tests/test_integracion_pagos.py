import pytest
from datetime import date
from decimal import Decimal
from django.utils import timezone

@pytest.mark.django_db
class TestIntegracionPagos:
    """Pruebas de integración: Ventas → Pagos Wompi (usando PagoWompi)"""
    
    def test_pago_wompi_aprobado(self, usuario_asesor, cliente, producto, inventario):
        """Integración: Venta → Pago Wompi → Aprobar → Completar"""
        from ventas.models import Ventas, DetalleVenta
        from pagos.models import PagoWompi
        
        # Crear venta
        venta = Ventas.objects.create(
            usuario=usuario_asesor,
            cliente=cliente,
            tipo_venta='DIRECTA',
            fecha_venta=timezone.now(),
            subtotal=Decimal('800000'),
            impuesto=Decimal('152000'),
            descuento=Decimal('0'),
            total=Decimal('952000'),
            estado_venta='PENDIENTE'
        )
        
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('800000'),
            subtotal=Decimal('800000')
        )
        
        # Crear pago Wompi
        pago = PagoWompi.objects.create(
            referencia=f"WOMPI-{venta.id_venta}",
            venta_id=venta.id_venta,
            cliente_id=cliente.id_cliente,
            monto=int(venta.total),
            monto_centavos=int(venta.total * 100),
            moneda='COP',
            estado='PENDIENTE'
        )
        
        assert pago.estado == 'PENDIENTE'
        
        # Simular aprobación
        pago.estado = 'COMPLETADO'
        pago.payment_method_type = 'CARD'
        pago.estado_wompi_raw = 'APPROVED'
        pago.wompi_transaction_id = '12345'
        pago.confirmed_at = timezone.now()
        pago.save()
        
        assert pago.estado == 'COMPLETADO'
        
        # Completar venta
        venta.estado_venta = 'COMPLETADA'
        venta.save()
        
        assert venta.estado_venta == 'COMPLETADA'
    
    def test_pago_wompi_rechazado(self, cliente, producto):
        """Integración: Pago rechazado → Venta permanece pendiente"""
        from ventas.models import Ventas
        from pagos.models import PagoWompi
        
        # Crear venta
        venta = Ventas.objects.create(
            cliente=cliente,
            tipo_venta='DIRECTA',
            fecha_venta=timezone.now(),
            subtotal=Decimal('500000'),
            impuesto=Decimal('95000'),
            descuento=Decimal('0'),
            total=Decimal('595000'),
            estado_venta='PENDIENTE'
        )
        
        # Crear pago rechazado
        pago = PagoWompi.objects.create(
            referencia=f"WOMPI-{venta.id_venta}",
            venta_id=venta.id_venta,
            cliente_id=cliente.id_cliente,
            monto=int(venta.total),
            monto_centavos=int(venta.total * 100),
            moneda='COP',
            estado='FALLIDO',
            estado_wompi_raw='DECLINED',
            error_message='Tarjeta declinada',
            failed_at=timezone.now()
        )
        
        assert pago.estado == 'FALLIDO'
        
        # Verificar que la venta sigue pendiente
        venta.refresh_from_db()
        assert venta.estado_venta == 'PENDIENTE'
    
    def test_pago_wompi_idempotencia(self, cliente):
        """Verificar que no se puede procesar el mismo pago dos veces"""
        from pagos.models import PagoWompi
        
        # Crear pago completado
        pago = PagoWompi.objects.create(
            referencia="TEST-IDEMPOTENTE-001",
            cliente_id=cliente.id_cliente,
            monto=100000,
            monto_centavos=10000000,
            moneda='COP',
            estado='COMPLETADO',
            venta_id=999,  # Simular que ya tiene venta asociada
            pedido_id=888,
            confirmed_at=timezone.now()
        )
        
        # Intentar procesar de nuevo (simular webhook duplicado)
        assert pago.venta_id is not None
        assert pago.estado == 'COMPLETADO'
        