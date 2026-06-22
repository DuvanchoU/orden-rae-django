import pytest
from datetime import date, timedelta
from decimal import Decimal


@pytest.mark.django_db
class TestIntegracionCotizaciones:
    """Pruebas de integración: Cotizaciones + Ventas + Clientes"""
    
    def test_flujo_cotizacion_completo(self, usuario_asesor, cliente, producto):
        """Integración: Crear cotización → Enviar → Aceptar → Convertir en venta"""
        from ventas.models import Cotizaciones, DetalleCotizacion
        
        # 1. Crear cotización (sin valores predefinidos para evitar validación)
        cotizacion = Cotizaciones.objects.create(
            cliente=cliente,
            usuario=usuario_asesor,
            fecha_cotizacion=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=30),
            estado='borrador',
            validez_dias=30,
            subtotal=Decimal('0'),
            impuesto=Decimal('0'),
            descuento=Decimal('0'),
            total=Decimal('0')
        )
        
        assert cotizacion.estado == 'borrador'
        assert cotizacion.puede_modificarse() is True
        
        # 2. Agregar productos
        DetalleCotizacion.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal('800000'),
            subtotal=Decimal('1600000')
        )
        
        # 3. Calcular totales (con quantize para 2 decimales)
        cotizacion.calcular_totales()
        
        assert cotizacion.subtotal == Decimal('1600000')
        assert cotizacion.impuesto > 0
        
        # 4. Enviar cotización
        cotizacion.estado = 'enviada'
        cotizacion.save()
        
        assert cotizacion.puede_modificarse() is True
        
        # 5. Cliente acepta
        cotizacion.estado = 'aceptada'
        cotizacion.save()
        
        assert cotizacion.puede_convertirse_en_venta()[0] is True
        
        # 6. Convertir en venta
        venta = cotizacion.convertir_en_venta(usuario=usuario_asesor)
        
        assert venta is not None
        assert venta.tipo_venta == 'DESDE_COTIZACION'
        assert cotizacion.venta_id == venta.id_venta
    
    def test_cotizacion_vencida_no_se_puede_convertir(self, cliente, producto):
        """Integración: Cotización vencida → No se puede convertir"""
        from ventas.models import Cotizaciones
        
        cotizacion = Cotizaciones.objects.create(
            cliente=cliente,
            fecha_cotizacion=date.today() - timedelta(days=60),
            fecha_vencimiento=date.today() - timedelta(days=30),
            estado='aceptada',
            subtotal=Decimal('800000'),
            impuesto=Decimal('152000'),
            descuento=Decimal('0'),
            total=Decimal('952000')
        )
        
        assert cotizacion.esta_vencida() is True
        
        puede, mensaje = cotizacion.puede_convertirse_en_venta()
        assert puede is False
    
    def test_cotizacion_con_descuento(self, cliente, producto):
        """Integración: Cotización con descuento"""
        from ventas.models import Cotizaciones, DetalleCotizacion
        
        cotizacion = Cotizaciones.objects.create(
            cliente=cliente,
            fecha_cotizacion=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=30),
            estado='borrador',
            descuento=Decimal('0'),
            subtotal=Decimal('0'),
            impuesto=Decimal('0'),
            total=Decimal('0')
        )
        
        DetalleCotizacion.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('800000'),
            descuento=Decimal('100000'),
            subtotal=Decimal('700000')
        )
        
        cotizacion.calcular_totales()
        
        assert cotizacion.total > 0