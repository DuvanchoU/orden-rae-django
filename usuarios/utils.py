# usuarios/utils.py
from django.core.cache import cache
from datetime import datetime, timedelta

def get_login_attempts(request):
    """Obtener número de intentos de login fallidos"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    return cache.get(key, 0)

def increment_login_attempts(request):
    """Incrementar contador de intentos fallidos"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, timeout=900)  # 15 minutos
    return attempts

def reset_login_attempts(request):
    """Resetear contador tras login exitoso"""
    ip = get_client_ip(request)
    key = f'login_attempts_{ip}'
    cache.delete(key)

def is_login_blocked(request):
    """Verificar si la IP está bloqueada temporalmente"""
    ip = get_client_ip(request)
    key = f'login_blocked_{ip}'
    return cache.get(key, False)

def block_login(request, duration=900):
    """Bloquear login por 15 minutos después de 5 intentos fallidos"""
    ip = get_client_ip(request)
    key = f'login_blocked_{ip}'
    cache.set(key, True, timeout=duration)

def get_client_ip(request):
    """Obtener IP real del cliente (funciona detrás de proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

"""
Helpers compartidos para todos los módulos de prueba.
Importar desde cualquier test_*.py así:
    from tests.utils import crear_rol, crear_usuario, crear_cliente, ...
"""

from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.db.models import Model


# ─────────────────────────────────────────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────────────────────────────────────────

def crear_rol(nombre="GERENTE", descripcion="Rol de prueba"):
    """
    Crea un RolesOld limpiando duplicados primero.
    Evita pasar por full_clean para no chocar con la validación
    de 'roles del sistema'.
    """
    from usuarios.models import RolesOld
    RolesOld.objects.filter(nombre_rol=nombre).delete()
    rol = RolesOld(nombre_rol=nombre, descripcion=descripcion)
    rol.save()
    return rol


def crear_usuario(rol, correo="test@test.com", nombres="Test",
                    apellidos="User", documento="12345678",
                    contrasena="TestPass1", estado="ACTIVO"):
    """
    Crea un Usuarios con contraseña ya hasheada, sin pasar por full_clean
    (que rechazaría el hash pbkdf2_ al validar fortaleza de contraseña).
    """
    from usuarios.models import Usuarios
    Usuarios.objects.filter(correo_usuario=correo).delete()
    Usuarios.objects.filter(documento=documento).delete()

    u = Usuarios(
        nombres=nombres,
        apellidos=apellidos,
        documento=documento,
        correo_usuario=correo,
        contrasena_usuario=make_password(contrasena),
        id_rol=rol,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
        fecha_registro=timezone.now(),
    )
    # Guardamos saltando full_clean para no revalidar el hash
    Model.save(u)
    return u


def autenticar_sesion(client, usuario):
    """
    Inyecta la sesión de staff en el cliente de prueba.
    Usa esto en lugar de client.login() porque el proyecto
    usa sesión personalizada (usuario_id) en vez de Django auth.
    """
    session = client.session
    session["usuario_id"] = usuario.pk
    session["usuario_nombre"] = usuario.get_full_name()
    session["usuario_rol"] = (
        usuario.id_rol.nombre_rol if usuario.id_rol else "SIN_ROL"
    )
    session.save()


# ─────────────────────────────────────────────────────────────────────────────
# VENTAS / CLIENTES
# ─────────────────────────────────────────────────────────────────────────────

def crear_cliente(nombre="Cliente", apellido="Test",
                    email="cliente@test.com", documento="87654321",
                    estado="ACTIVO"):
    """Crea un Clientes de prueba."""
    from ventas.models import Clientes
    from django.db.models import Model
    Clientes.objects.filter(email=email).delete()
    Clientes.objects.filter(documento=documento).delete()

    c = Clientes(
        nombre=nombre,
        apellido=apellido,
        email=email,
        documento=documento,
        contrasena_cliente=make_password("ClientePass1"),
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
        fecha_registro=timezone.now(),
    )
    Model.save(c)
    return c


def crear_pedido(cliente, usuario=None, estado="PENDIENTE"):
    """Crea un Pedido de prueba."""
    from ventas.models import Pedido
    from django.db.models import Model
    p = Pedido(
        cliente=cliente,
        usuario=usuario,
        estado_pedido=estado,
        total_pedido=0,
        created_at=timezone.now(),
        updated_at=timezone.now(),
        fecha_pedido=timezone.now(),
    )
    Model.save(p)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# INVENTARIO
# ─────────────────────────────────────────────────────────────────────────────

def crear_categoria(nombre="CATEGORIA TEST"):
    """Crea una Categorias de prueba."""
    from inventario.models import Categorias
    Categorias.objects.filter(nombre_categoria=nombre).delete()
    cat = Categorias(
        nombre_categoria=nombre,
        estado_categoria="activo",
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    cat.save()
    return cat


def crear_producto(categoria, codigo="PROD-001",
                    referencia="Producto de prueba",
                    precio=100000, estado="DISPONIBLE"):
    """Crea un Producto de prueba."""
    from inventario.models import Producto
    from django.db.models import Model
    Producto.objects.filter(codigo_producto=codigo).delete()

    p = Producto(
        codigo_producto=codigo,
        referencia_producto=referencia,
        categoria=categoria,
        precio_actual=precio,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(p)
    return p


def crear_proveedor(nombre="Proveedor Test", estado="ACTIVO"):
    """Crea un Proveedores de prueba."""
    from inventario.models import Proveedores
    Proveedores.objects.filter(nombre=nombre).delete()
    prov = Proveedores(
        nombre=nombre,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    prov.save()
    return prov


def crear_bodega(nombre="Bodega Principal", estado="ACTIVA"):
    """Crea una Bodegas de prueba."""
    from inventario.models import Bodegas
    Bodegas.objects.filter(nombre_bodega=nombre).delete()
    b = Bodegas(
        nombre_bodega=nombre,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    b.save()
    return b


# ─────────────────────────────────────────────────────────────────────────────
# COMPRAS
# ─────────────────────────────────────────────────────────────────────────────

def crear_compra(proveedor, usuario=None, estado="PENDIENTE"):
    """Crea una Compras de prueba."""
    from compras.models import Compras
    from django.db.models import Model
    c = Compras(
        proveedor=proveedor,
        usuario=usuario,
        fecha_compra=timezone.now().date(),
        total_compra=0,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(c)
    return c


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def crear_produccion(producto, cantidad=10, estado="PENDIENTE"):
    """Crea una Produccion de prueba."""
    from produccion.models import Produccion
    from django.db.models import Model
    p = Produccion(
        producto=producto,
        cantidad_producida=cantidad,
        estado_produccion=estado,
        fecha_inicio=timezone.now().date(),
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(p)
    return p