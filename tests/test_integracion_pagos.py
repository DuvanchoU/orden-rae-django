import pytest
from datetime import date
from decimal import Decimal
from django.utils import timezone


@pytest.mark.django_db
class TestIntegracionPagos:
    """Pruebas de integración: Ventas → Pagos Wompi"""
    
    def test_transaccion_wompi_aprobada(self, usuario_asesor, cliente, producto, inventario):
        """Integración: Venta → Transacción Wompi → Aprobar → Completar"""
        from ventas.models import Ventas, DetalleVenta, TransaccionWompi
        
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
        
        transaccion = TransaccionWompi.objects.create(
            venta=venta,
            referencia=f"WOMPI-{venta.id_venta}",
            monto=venta.total,
            estado='PENDING',
            es_sandbox=True
        )
        
        assert transaccion.estado == 'PENDING'
        
        transaccion.estado = 'APPROVED'
        transaccion.metodo_pago = 'CARD'
        transaccion.respuesta_wompi = {
            'status': 'APPROVED',
            'transaction_id': '12345'
        }
        transaccion.save()
        
        assert transaccion.estado == 'APPROVED'
        
        venta.completar_venta()
        
        assert venta.estado_venta == 'COMPLETADA'
    
    def test_transaccion_wompi_rechazada(self, cliente, producto):
        """Integración: Transacción rechazada → Venta permanece pendiente"""
        from ventas.models import Ventas, TransaccionWompi
        
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
        
        transaccion = TransaccionWompi.objects.create(
            venta=venta,
            referencia=f"WOMPI-{venta.id_venta}",
            monto=venta.total,
            estado='DECLINED',
            es_sandbox=True
        )
        
        assert transaccion.estado == 'DECLINED'
        
        venta.refresh_from_db()
        assert venta.estado_venta == 'PENDIENTE'