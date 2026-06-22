import pytest
import hashlib
from django.test import Client, override_settings
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal


# ✅ FIX CRÍTICO: Override de STATICFILES_STORAGE para TODOS los tests
@pytest.fixture(autouse=True, scope='function')
def _override_staticfiles_storage(settings):
    """Evita el error de manifest en tests"""
    # Override directo del setting
    settings.STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
    # También desactivar el manifest strict
    settings.DEBUG = True
    yield


# ==================== FIXTURES USUARIOS ====================

@pytest.fixture
def rol_gerente():
    """Fixture: Crear rol de gerente"""
    from usuarios.models import RolesOld
    rol, _ = RolesOld.objects.get_or_create(
        nombre_rol='GERENTE',
        defaults={'descripcion': 'Acceso completo al sistema'}
    )
    return rol


@pytest.fixture
def rol_asesor():
    """Fixture: Crear rol de asesor comercial"""
    from usuarios.models import RolesOld
    rol, _ = RolesOld.objects.get_or_create(
        nombre_rol='ASESOR COMERCIAL',
        defaults={'descripcion': 'Gestión de ventas'}
    )
    return rol


@pytest.fixture
def usuario_admin(rol_gerente):
    """Fixture: Crear usuario administrador (Gerente)"""
    from usuarios.models import Usuarios
    usuario, _ = Usuarios.objects.get_or_create(
        correo_usuario='admin@ordenrae.com',
        defaults={
            'nombres': 'Admin',
            'apellidos': 'Test',
            'documento': '9999999999',
            'contrasena_usuario': hashlib.sha256('Admin123'.encode()).hexdigest(),
            'telefono': '3001234567',
            'genero': 'M',
            'id_rol': rol_gerente,
            'estado': 'ACTIVO',
            'fecha_registro': timezone.now()
        }
    )
    return usuario


@pytest.fixture
def usuario_asesor(rol_asesor):
    """Fixture: Crear usuario asesor"""
    from usuarios.models import Usuarios
    usuario, _ = Usuarios.objects.get_or_create(
        correo_usuario='asesor@ordenrae.com',
        defaults={
            'nombres': 'Juan',
            'apellidos': 'Pérez',
            'documento': '1234567890',
            'contrasena_usuario': hashlib.sha256('Asesor123'.encode()).hexdigest(),
            'telefono': '3009876543',
            'genero': 'M',
            'id_rol': rol_asesor,
            'estado': 'ACTIVO',
            'fecha_registro': timezone.now()
        }
    )
    return usuario


# ==================== FIXTURES INVENTARIO ====================

@pytest.fixture
def bodega():
    """Fixture: Crear bodega"""
    from inventario.models import Bodegas
    bodega, _ = Bodegas.objects.get_or_create(
        nombre_bodega='Bodega Principal',
        defaults={
            'direccion': 'Calle 123 #45-67',
            'estado': 'ACTIVA'
        }
    )
    return bodega


@pytest.fixture
def categoria():
    """Fixture: Crear categoría"""
    from inventario.models import Categorias
    categoria, _ = Categorias.objects.get_or_create(
        nombre_categoria='Muebles',
        defaults={'estado_categoria': 'activo'}
    )
    return categoria


@pytest.fixture
def proveedor():
    """Fixture: Crear proveedor"""
    from inventario.models import Proveedores
    proveedor, _ = Proveedores.objects.get_or_create(
        nombre='Muebles S.A.',
        defaults={
            'telefono': '6012345678',
            'email': 'contacto@mueblessa.com',
            'direccion': 'Zona Industrial',
            'estado': 'ACTIVO'
        }
    )
    return proveedor


@pytest.fixture
def producto(categoria):
    """Fixture: Crear producto"""
    from inventario.models import Producto
    producto, _ = Producto.objects.get_or_create(
        codigo_producto='SOF-001',
        defaults={
            'referencia_producto': 'Sofá 3 puestos',
            'categoria': categoria,
            'precio_actual': 800000,
            'estado': 'DISPONIBLE'
        }
    )
    return producto


@pytest.fixture
def inventario(producto, bodega, proveedor):
    """Fixture: Crear registro de inventario con stock"""
    from inventario.models import Inventario
    inventario, _ = Inventario.objects.get_or_create(
        producto=producto,
        bodega=bodega,
        defaults={
            'cantidad_disponible': 20,
            'cantidad_reservada': 0,
            'proveedor': proveedor,
            'estado': 'DISPONIBLE'
        }
    )
    return inventario


# ==================== FIXTURES VENTAS ====================

@pytest.fixture
def cliente():
    """Fixture: Crear cliente"""
    from ventas.models import Clientes
    cliente, _ = Clientes.objects.get_or_create(
        email='juan@cliente.com',
        defaults={
            'nombre': 'Juan',
            'apellido': 'Pérez',
            'documento': '1234567890',
            'genero': 'M',
            'telefono': '3009876543',
            'direccion': 'Calle 123 #45-67',
            'estado': 'ACTIVO',
            'fecha_registro': timezone.now(),
            'email_verificado': True
        }
    )
    return cliente


@pytest.fixture
def metodo_pago():
    """Fixture: Crear método de pago"""
    from ventas.models import MetodosPago
    metodo, _ = MetodosPago.objects.get_or_create(
        nombre='EFECTIVO',
        defaults={'descripcion': 'Pago en efectivo'}
    )
    return metodo


@pytest.fixture
def carrito(cliente):
    """Fixture: Crear carrito de compras"""
    from ventas.models import Carritos
    carrito, _ = Carritos.objects.get_or_create(
        cliente=cliente,
        defaults={'session_id': 'test-session-123'}
    )
    return carrito


@pytest.fixture
def cotizacion(cliente, producto):
    """Fixture: Crear cotización"""
    from ventas.models import Cotizaciones
    cotizacion, _ = Cotizaciones.objects.get_or_create(
        numero_cotizacion='COT-000001',
        defaults={
            'cliente': cliente,
            'fecha_cotizacion': date.today(),
            'fecha_vencimiento': date.today() + timedelta(days=30),
            'estado': 'aceptada',
            'subtotal': Decimal('800000'),
            'impuesto': Decimal('152000'),
            'descuento': Decimal('0'),
            'total': Decimal('952000'),
            'validez_dias': 30
        }
    )
    return cotizacion


@pytest.fixture
def pedido(cliente, producto):
    """Fixture: Crear pedido"""
    from ventas.models import Pedido
    pedido, _ = Pedido.objects.get_or_create(
        numero_pedido='PED-000001',
        defaults={
            'cliente': cliente,
            'fecha_pedido': timezone.now(),
            'fecha_entrega_estimada': date.today() + timedelta(days=7),
            'total_pedido': Decimal('800000'),
            'estado_pedido': 'PENDIENTE',
            'direccion_entrega': 'Calle 123 #45-67',
            'estado_facturacion': 'NO_FACTURADO'
        }
    )
    return pedido


@pytest.fixture
def client():
    """Fixture: Cliente HTTP de Django"""
    return Client()