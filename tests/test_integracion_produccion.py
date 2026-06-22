import pytest
from django.urls import reverse
from datetime import date
from produccion.models import Produccion


@pytest.mark.django_db
class TestIntegracionProduccion:
    """Pruebas de integración: Producción + Inventario + Pedidos"""
    
    def test_flujo_completo_produccion(self, producto, proveedor):
        """
        Integración: Crear producción → En proceso → Terminada
        """
        # 1. Crear orden de producción
        produccion = Produccion.objects.create(
            producto=producto,
            cantidad_producida=10,
            fecha_inicio=date.today(),
            estado_produccion='PENDIENTE',
            proveedor=proveedor
        )
        
        assert produccion.estado_produccion == 'PENDIENTE'
        
        # 2. Cambiar a en proceso
        produccion.cambiar_estado('EN PROCESO')
        assert produccion.estado_produccion == 'EN PROCESO'
        
        # 3. Cambiar a terminada
        produccion.cambiar_estado('TERMINADA')
        assert produccion.estado_produccion == 'TERMINADA'
        assert produccion.fecha_fin is not None
    
    def test_produccion_no_se_puede_modificar_si_terminada(self, producto, proveedor):
        """
        Integración: Producción terminada → No se puede modificar
        """
        produccion = Produccion.objects.create(
            producto=producto,
            cantidad_producida=10,
            fecha_inicio=date.today(),
            estado_produccion='TERMINADA',
            proveedor=proveedor
        )
        
        # Intentar cambiar estado
        with pytest.raises(Exception):
            produccion.cambiar_estado('PENDIENTE')
    
    def test_produccion_cantidad_asignada(self, producto, proveedor):
        """
        Integración: Producción → Asignación a pedidos
        """
        produccion = Produccion.objects.create(
            producto=producto,
            cantidad_producida=10,
            fecha_inicio=date.today(),
            estado_produccion='EN PROCESO',
            proveedor=proveedor
        )
        
        # Verificar cantidad disponible
        assert produccion.get_cantidad_disponible() == 10
        assert produccion.esta_completamente_asignada() is False