import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone


@pytest.mark.django_db
class TestIntegracionFlujoVentas:
    """Pruebas de integración: Cliente → Carrito → Pedido → Venta"""
    
    def test_flujo_completo_venta(self, usuario_asesor, cliente, producto, inventario, metodo_pago):
        """Integración completa: Pedido → Venta → Actualizar inventario"""
        from ventas.models import Pedido, DetallePedido, Ventas, DetalleVenta
        
        inventario.refresh_from_db()
        stock_inicial = inventario.cantidad_disponible
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            asesor=usuario_asesor,
            fecha_pedido=timezone.now(),
            fecha_entrega_estimada=date.today() + timedelta(days=7),
            estado_pedido='PENDIENTE',
            direccion_entrega='Calle 123 #45-67',
            total_pedido=Decimal('0')
        )
        
        DetallePedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal('800000')
        )
        
        pedido.calcular_total()
        
        assert pedido.total_pedido == Decimal('1600000')
        
        pedido.cambiar_estado('CONFIRMADO')
        assert pedido.estado_pedido == 'CONFIRMADO'
        
        venta = Ventas.objects.create(
            usuario=usuario_asesor,
            cliente=cliente,
            pedido=pedido,
            tipo_venta='DESDE_PEDIDO',
            fecha_venta=timezone.now(),
            subtotal=Decimal('1600000'),
            impuesto=Decimal('304000'),
            descuento=Decimal('0'),
            total=Decimal('1904000'),
            estado_venta='PENDIENTE',
            metodo_pago=metodo_pago
        )
        
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=2,
            precio_unitario=Decimal('800000'),
            subtotal=Decimal('1600000')
        )
        
        venta.calcular_totales()
        
        assert venta.total > 0
        
        venta.completar_venta()
        
        assert venta.estado_venta == 'COMPLETADA'
        
        pedido.refresh_from_db()
        assert pedido.estado_pedido == 'COMPLETADO'
        assert pedido.estado_facturacion == 'FACTURADO'
    
    def test_cotizacion_a_venta(self, usuario_asesor, producto):
        """Integración: Cotización aceptada → Convertir en venta"""
        from ventas.models import Cotizaciones, DetalleCotizacion, Clientes
        
        cliente = Clientes.objects.create(
            nombre='Test',
            apellido='Cliente',
            email='test2@cliente.com',
            estado='ACTIVO',
            email_verificado=True
        )
        
        cotizacion = Cotizaciones.objects.create(
            cliente=cliente,
            fecha_cotizacion=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=30),
            estado='aceptada',
            subtotal=Decimal('0'),
            impuesto=Decimal('0'),
            descuento=Decimal('0'),
            total=Decimal('0')
        )
        
        DetalleCotizacion.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('800000'),
            subtotal=Decimal('800000')
        )
        
        puede, mensaje = cotizacion.puede_convertirse_en_venta()
        assert puede is True
        
        venta = cotizacion.convertir_en_venta(usuario=usuario_asesor)
        
        assert venta is not None
        assert venta.tipo_venta == 'DESDE_COTIZACION'
        
        cotizacion.refresh_from_db()
        assert cotizacion.venta_id == venta.id_venta
    
    def test_carrito_a_pedido(self, cliente, carrito, producto):
        """Integración: Carrito → Crear pedido"""
        from ventas.models import ItemsCarrito, Pedido, DetallePedido
        
        ItemsCarrito.objects.create(
            carrito=carrito,
            producto=producto,
            cantidad=3,
            precio_unitario=Decimal('800000')
        )
        
        assert ItemsCarrito.objects.filter(carrito=carrito).count() == 1
        
        pedido = Pedido.objects.create(
            cliente=cliente,
            fecha_pedido=timezone.now(),
            estado_pedido='PENDIENTE',
            total_pedido=Decimal('0')
        )
        
        for item in ItemsCarrito.objects.filter(carrito=carrito):
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario
            )
        
        pedido.calcular_total()
        
        assert pedido.total_pedido == Decimal('2400000')
        
        ItemsCarrito.objects.filter(carrito=carrito).delete()
        
        assert ItemsCarrito.objects.filter(carrito=carrito).count() == 0
    
    def test_venta_con_descuento(self, usuario_asesor, cliente, producto, metodo_pago):
        """Integración: Venta con descuento"""
        from ventas.models import Ventas, DetalleVenta
        
        venta = Ventas.objects.create(
            usuario=usuario_asesor,
            cliente=cliente,
            tipo_venta='DIRECTA',
            fecha_venta=timezone.now(),
            subtotal=Decimal('800000'),
            impuesto=Decimal('152000'),
            descuento=Decimal('50000'),
            total=Decimal('902000'),
            estado_venta='PENDIENTE',
            metodo_pago=metodo_pago
        )
        
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=1,
            precio_unitario=Decimal('800000'),
            descuento=Decimal('50000'),
            subtotal=Decimal('750000')
        )
        
        venta.calcular_totales()
        
        assert venta.subtotal == Decimal('750000')
        assert venta.total > 0