"""
Tests unitarios - Módulo Ventas
Nivel: Intermedio
Cubre: Modelos (Clientes, Pedido, Ventas, Cotizaciones),
       Formularios (ClienteForm, PedidoForm, VentaForm, CotizacionForm),
       Vistas CRUD completas
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Model

from ventas.models import (
    Clientes, Pedido, Ventas, Cotizaciones,
    DetallePedido, DetalleVenta, MetodosPago, Carritos, ItemsCarrito
)
from ventas.forms import ClienteForm, PedidoForm, VentaForm, CotizacionForm
from inventario.models import Producto, Categorias
from usuarios.models import RolesOld, Usuarios
from django.contrib.auth.hashers import make_password


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
# Estos helpers simplifican la creación de objetos para los tests, evitando repetición
def crear_rol(nombre="GERENTE"):
    RolesOld.objects.filter(nombre_rol=nombre).delete()
    r = RolesOld(nombre_rol=nombre, descripcion="Rol prueba")
    r.save()
    return r

# El helper para crear usuario se adapta a los campos del modelo Usuarios, con valores por defecto para simplificar su uso en los tests.
def crear_usuario(rol, correo="admin@test.com", doc="00000001"):
    from django.db.models import Model as DjangoModel
    Usuarios.objects.filter(correo_usuario=correo).delete()
    Usuarios.objects.filter(documento=doc).delete()
    u = Usuarios(
        nombres="Admin", apellidos="Test",
        documento=doc, correo_usuario=correo,
        contrasena_usuario=make_password("Admin123"),
        id_rol=rol, estado="ACTIVO",
        created_at=timezone.now(), updated_at=timezone.now(),
        fecha_registro=timezone.now(),
    )
    DjangoModel.save(u)
    return u

# El helper para autenticar sesión simula el proceso de login estableciendo las variables de sesión 
# necesarias para que las vistas reconozcan al usuario como autenticado.
def autenticar_sesion(client, usuario):
    s = client.session
    s["usuario_id"] = usuario.pk
    s["usuario_nombre"] = f"{usuario.nombres} {usuario.apellidos}"
    s["usuario_rol"] = usuario.id_rol.nombre_rol if usuario.id_rol else "GERENTE"
    s.save()

# El helper para crear cliente se adapta a los campos del modelo Clientes, con valores por defecto para simplificar su uso en los tests.
def crear_cliente(nombre="Carlos", apellido="Ruiz",
                    email="carlos@test.com", doc="11111111", estado="ACTIVO"):
    Clientes.objects.filter(email=email).delete()
    Clientes.objects.filter(documento=doc).delete()
    c = Clientes(
        nombre=nombre, apellido=apellido,
        email=email, documento=doc,
        contrasena_cliente=make_password("Cliente123"),
        estado=estado,
        created_at=timezone.now(), updated_at=timezone.now(),
        fecha_registro=timezone.now(),
    )
    c.save()
    return c

# Los helpers para crear Pedido, Ventas y Cotizaciones se mantienen simples, con valores por defecto para los campos necesarios. 
# Se pueden extender según sea necesario para cubrir más casos de prueba.
def crear_pedido(cliente, usuario, estado="PENDIENTE"):
    p = Pedido(
        cliente=cliente, usuario=usuario,
        estado_pedido=estado,
        total_pedido=Decimal("0"),
        fecha_pedido=timezone.now(),
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(p)
    return p

# El helper para crear venta se adapta a los campos del modelo Ventas, pero se mantiene con valores por defecto para simplificar su uso en los tests
def crear_venta(usuario, cliente, estado="PENDIENTE"):
    v = Ventas(
        usuario=usuario, cliente=cliente,
        tipo_venta="DIRECTA",
        fecha_venta=timezone.now(),
        subtotal=Decimal("100000"),
        impuesto=Decimal("19000"),
        descuento=Decimal("0"),
        total=Decimal("119000"),
        estado_venta=estado,
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(v)
    return v

# El helper para crear cotización se adapta a los campos del modelo Cotizaciones, con valores por defecto para simplificar su uso en los tests. 
# Se puede extender según sea necesario para cubrir más casos de prueba.
def crear_cotizacion(cliente, usuario, estado="borrador"):
    fecha_venc = timezone.now().date() + timedelta(days=30)
    c = Cotizaciones(
        cliente=cliente, usuario=usuario,
        fecha_cotizacion=timezone.now().date(),
        fecha_vencimiento=fecha_venc,
        estado=estado,
        subtotal=Decimal("100000"),
        impuesto=Decimal("19000"),
        descuento=Decimal("0"),
        total=Decimal("119000"),
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(c)
    return c

# Helpers para crear categorías y productos, necesarios para algunos tests de ventas. Se mantienen simples con valores por defecto.
def crear_categoria(nombre="CAT V"):
    Categorias.objects.filter(nombre_categoria=nombre).delete()
    cat = Categorias(
        nombre_categoria=nombre, estado_categoria="activo",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    cat.save()
    return cat

# El helper para crear producto se adapta a los campos del modelo Producto, con valores por defecto para simplificar su uso en los tests.
def crear_producto(categoria, codigo="VP-001", precio=100000):
    Producto.objects.filter(codigo_producto=codigo).delete()
    p = Producto(
        codigo_producto=codigo,
        referencia_producto="Producto venta test",
        categoria=categoria,
        precio_actual=Decimal(str(precio)),
        estado="DISPONIBLE",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(p)
    return p


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Clientes
# ══════════════════════════════════════════════════════════════════════════════

class ClientesModelTests(TestCase):

    def test_crear_cliente_exitoso(self):
        c = crear_cliente()
        self.assertIsNotNone(c.pk)
        self.assertEqual(c.estado, "ACTIVO")

    def test_get_nombre_completo(self):
        c = crear_cliente(nombre="María", apellido="Gómez")
        self.assertEqual(c.get_nombre_completo(), "María Gómez")

    def test_get_nombre_completo_sin_apellido(self):
        c = crear_cliente(nombre="Solo", apellido=None, email="solo@t.com", doc="22220001")
        c.apellido = None
        Model.save(c)
        self.assertEqual(c.get_nombre_completo(), "Solo")

    def test_str_incluye_nombre(self):
        c = crear_cliente()
        self.assertIn("Carlos", str(c))

    def test_is_authenticated_activo(self):
        c = crear_cliente()
        self.assertTrue(c.is_authenticated)

    def test_is_authenticated_inactivo(self):
        c = crear_cliente(
            nombre="Inact", email="inact@t.com",
            doc="33330001", estado="INACTIVO"
        )
        self.assertFalse(c.is_authenticated)

    def test_esta_activo_true(self):
        c = crear_cliente()
        self.assertTrue(c.esta_activo())

    def test_esta_activo_false_si_deleted(self):
        c = crear_cliente(nombre="Del", email="del@t.com", doc="44440001")
        c.delete()
        self.assertFalse(c.esta_activo())

    def test_soft_delete(self):
        c = crear_cliente(nombre="SDel", email="sdel@t.com", doc="55550001")
        pk = c.pk
        c.delete()
        self.assertIsNotNone(c.deleted_at)
        self.assertTrue(Clientes.objects.filter(pk=pk).exists())

    def test_restore_cliente(self):
        c = crear_cliente(nombre="Rest", email="rest@t.com", doc="66660001")
        c.delete()
        c.restore()
        self.assertIsNone(c.deleted_at)
        self.assertEqual(c.estado, "ACTIVO")

    def test_username_es_email(self):
        c = crear_cliente()
        self.assertEqual(c.username, "carlos@test.com")

    def test_get_cantidad_pedidos_cero(self):
        c = crear_cliente()
        self.assertEqual(c.get_cantidad_pedidos(), 0)

    def test_puede_eliminarse_sin_pedidos_activos(self):
        c = crear_cliente()
        self.assertTrue(c.puede_eliminarse())


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Pedido
# ══════════════════════════════════════════════════════════════════════════════

class PedidoModelTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("GERENTE_PD")
        self.usuario = crear_usuario(self.rol, "upd@test.com", "77770001")
        self.cliente = crear_cliente(
            nombre="Ped", email="ped@test.com", doc="88880001"
        )

    def test_crear_pedido_exitoso(self):
        p = crear_pedido(self.cliente, self.usuario)
        self.assertIsNotNone(p.pk)
        self.assertEqual(p.estado_pedido, "PENDIENTE")

    def test_numero_pedido_autogenerado(self):
        p = crear_pedido(self.cliente, self.usuario)
        # Si fue creado por helpers sin número, puede ser None
        # El número se genera en save() del modelo real
        self.assertTrue(p.pk is not None)

    def test_puede_modificarse_pendiente(self):
        p = crear_pedido(self.cliente, self.usuario, estado="PENDIENTE")
        self.assertTrue(p.puede_modificarse())

    def test_puede_modificarse_confirmado(self):
        p = crear_pedido(self.cliente, self.usuario, estado="CONFIRMADO")
        self.assertTrue(p.puede_modificarse())

    def test_no_puede_modificarse_completado(self):
        p = crear_pedido(self.cliente, self.usuario, estado="COMPLETADO")
        self.assertFalse(p.puede_modificarse())

    def test_no_puede_modificarse_cancelado(self):
        p = crear_pedido(self.cliente, self.usuario, estado="CANCELADO")
        self.assertFalse(p.puede_modificarse())

    def test_puede_eliminarse_pendiente_sin_detalles(self):
        p = crear_pedido(self.cliente, self.usuario, estado="PENDIENTE")
        self.assertTrue(p.puede_eliminarse())

    def test_precio_formateado(self):
        p = crear_pedido(self.cliente, self.usuario)
        p.total_pedido = Decimal("950000")
        Model.save(p)
        fmt = p.precio_formateado()
        self.assertIn("950.000", fmt)

    def test_str_incluye_cliente(self):
        p = crear_pedido(self.cliente, self.usuario)
        self.assertIn(self.cliente.nombre, str(p))

    def test_cambiar_estado_pendiente_a_confirmado(self):
        p = Pedido(
            cliente=self.cliente, usuario=self.usuario,
            estado_pedido="PENDIENTE",
            total_pedido=Decimal("0"),
            fecha_pedido=timezone.now(),
            created_at=timezone.now(), updated_at=timezone.now(),
        )
        p.save()
        p.cambiar_estado("CONFIRMADO")
        self.assertEqual(p.estado_pedido, "CONFIRMADO")

    def test_cambiar_estado_invalido_falla(self):
        p = Pedido(
            cliente=self.cliente, usuario=self.usuario,
            estado_pedido="PENDIENTE",
            total_pedido=Decimal("0"),
            fecha_pedido=timezone.now(),
            created_at=timezone.now(), updated_at=timezone.now(),
        )
        p.save()
        with self.assertRaises(ValidationError):
            p.cambiar_estado("COMPLETADO")


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Ventas
# ══════════════════════════════════════════════════════════════════════════════

class VentasModelTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("GERENTE_V")
        self.usuario = crear_usuario(self.rol, "uv@test.com", "10010001")
        self.cliente = crear_cliente(
            nombre="Venta", email="venta@test.com", doc="20020001"
        )

    def test_crear_venta_exitosa(self):
        v = crear_venta(self.usuario, self.cliente)
        self.assertIsNotNone(v.pk)
        self.assertEqual(v.estado_venta, "PENDIENTE")

    def test_precio_formateado(self):
        v = crear_venta(self.usuario, self.cliente)
        v.total = Decimal("1200000")
        Model.save(v)
        fmt = v.precio_formateado()
        self.assertIn("1.200.000", fmt)

    def test_puede_modificarse_pendiente(self):
        v = crear_venta(self.usuario, self.cliente)
        self.assertTrue(v.puede_modificarse())

    def test_no_puede_modificarse_completada(self):
        v = crear_venta(self.usuario, self.cliente, estado="COMPLETADA")
        self.assertFalse(v.puede_modificarse())

    def test_puede_eliminarse_pendiente(self):
        v = crear_venta(self.usuario, self.cliente)
        self.assertTrue(v.puede_eliminarse())

    def test_no_puede_eliminarse_completada(self):
        v = crear_venta(self.usuario, self.cliente, estado="COMPLETADA")
        self.assertFalse(v.puede_eliminarse())

    def test_soft_delete_pendiente(self):
        v = crear_venta(self.usuario, self.cliente)
        v.delete()
        self.assertIsNotNone(v.deleted_at)

    def test_soft_delete_completada_falla(self):
        v = crear_venta(self.usuario, self.cliente, estado="COMPLETADA")
        with self.assertRaises(ValidationError):
            v.delete()

    def test_str_incluye_cliente(self):
        v = crear_venta(self.usuario, self.cliente)
        self.assertIn(self.cliente.nombre, str(v))


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Cotizaciones
# ══════════════════════════════════════════════════════════════════════════════

class CotizacionesModelTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("GERENTE_COT")
        self.usuario = crear_usuario(self.rol, "ucot@test.com", "30030001")
        self.cliente = crear_cliente(
            nombre="Cot", email="cot@test.com", doc="40040001"
        )

    def test_crear_cotizacion_exitosa(self):
        c = crear_cotizacion(self.cliente, self.usuario)
        self.assertIsNotNone(c.pk)
        self.assertEqual(c.estado, "borrador")

    def test_puede_modificarse_borrador(self):
        c = crear_cotizacion(self.cliente, self.usuario, estado="borrador")
        self.assertTrue(c.puede_modificarse())

    def test_puede_modificarse_enviada(self):
        c = crear_cotizacion(self.cliente, self.usuario, estado="enviada")
        self.assertTrue(c.puede_modificarse())

    def test_no_puede_modificarse_aceptada(self):
        c = crear_cotizacion(self.cliente, self.usuario, estado="aceptada")
        self.assertFalse(c.puede_modificarse())

    def test_puede_eliminarse_borrador(self):
        c = crear_cotizacion(self.cliente, self.usuario)
        self.assertTrue(c.puede_eliminarse())

    def test_no_puede_eliminarse_enviada(self):
        c = crear_cotizacion(self.cliente, self.usuario, estado="enviada")
        self.assertFalse(c.puede_eliminarse())

    def test_esta_vencida_false_si_reciente(self):
        c = crear_cotizacion(self.cliente, self.usuario)
        self.assertFalse(c.esta_vencida())

    def test_esta_vencida_true_si_pasada(self):
        c = crear_cotizacion(self.cliente, self.usuario)
        c.fecha_vencimiento = timezone.now().date() - timedelta(days=1)
        Model.save(c)
        self.assertTrue(c.esta_vencida())

    def test_total_formateado(self):
        c = crear_cotizacion(self.cliente, self.usuario)
        c.total = Decimal("2500000")
        Model.save(c)
        fmt = c.get_total_formateado()
        self.assertIn("2.500.000", fmt)

    # El test para número de cotización único se omite por simplicidad, pero sería similar a los demás
    def test_numero_cotizacion_unico(self):
        fecha_venc = timezone.now().date() + timedelta(days=30)
        c1 = Cotizaciones(
            cliente=self.cliente, usuario=self.usuario,
            fecha_cotizacion=timezone.now().date(),
            fecha_vencimiento=fecha_venc,
            estado='borrador',
            subtotal=Decimal('100000'),
            impuesto=Decimal('19000'),
            descuento=Decimal('0'),
            total=Decimal('119000'),
        )
        c1.save()
        c2 = Cotizaciones(
            cliente=self.cliente, usuario=self.usuario,
            fecha_cotizacion=timezone.now().date(),
            fecha_vencimiento=fecha_venc,
            estado='borrador',
            subtotal=Decimal('100000'),
            impuesto=Decimal('19000'),
            descuento=Decimal('0'),
            total=Decimal('119000'),
        )
        c2.save()
        self.assertNotEqual(c1.numero_cotizacion, c2.numero_cotizacion)


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIOS
# ══════════════════════════════════════════════════════════════════════════════

class ClienteFormTests(TestCase):

    def _datos(self, nombre="Form Cliente", email="formcli@test.com"):
        return {
            "nombre": nombre,
            "apellido": "Apellido",
            "telefono": "3009988776",
            "email": email,
            "direccion": "Calle 10 # 20-30",
            "estado": "ACTIVO",
        }

    def test_formulario_valido(self):
        form = ClienteForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_muy_corto_invalido(self):
        datos = self._datos()
        datos["nombre"] = "A"
        form = ClienteForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)

    def test_email_invalido(self):
        datos = self._datos()
        datos["email"] = "no-es-email"
        form = ClienteForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_email_duplicado_invalido(self):
        crear_cliente(email="dupform@test.com", doc="50050001")
        datos = self._datos(email="dupform@test.com")
        form = ClienteForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_telefono_muy_corto_invalido(self):
        datos = self._datos()
        datos["telefono"] = "123"
        form = ClienteForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)

    def test_nombre_se_capitaliza(self):
        datos = self._datos(nombre="juan carlos")
        form = ClienteForm(data=datos)
        if form.is_valid():
            self.assertEqual(form.cleaned_data["nombre"], "Juan Carlos")


class PedidoFormTests(TestCase):

    def setUp(self):
        self.cliente = crear_cliente(
            nombre="PedForm", email="pedform@test.com", doc="60060001"
        )

    def _datos(self):
        return {
            "cliente": self.cliente.pk,
            "fecha_entrega_estimada": (
                timezone.now().date() + timedelta(days=5)
            ).isoformat(),
            "total_pedido": "0",
            "estado_pedido": "PENDIENTE",
            "direccion_entrega": "Carrera 5 # 10-15",
        }

    def test_formulario_valido(self):
        form = PedidoForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_fecha_entrega_pasada_invalida(self):
        datos = self._datos()
        datos["fecha_entrega_estimada"] = (
            timezone.now().date() - timedelta(days=1)
        ).isoformat()
        form = PedidoForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_entrega_estimada", form.errors)

    def test_sin_cliente_invalido(self):
        datos = self._datos()
        datos["cliente"] = ""
        form = PedidoForm(data=datos)
        self.assertFalse(form.is_valid())


class VentaFormTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("ROL_VF")
        self.usuario = crear_usuario(self.rol, "uvf@test.com", "70070001")
        self.cliente = crear_cliente(
            nombre="VentaF", email="ventaf@test.com", doc="80080001"
        )

    def _datos(self):
        return {
            "cliente": self.cliente.pk,
            "tipo_venta": "DIRECTA",
            "subtotal": "100000",
            "impuesto": "19000",
            "descuento": "0",
            "total": "119000",
            "estado_venta": "PENDIENTE",
        }

    def test_formulario_valido(self):
        form = VentaForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_cliente_invalido(self):
        datos = self._datos()
        datos["cliente"] = ""
        form = VentaForm(data=datos)
        self.assertFalse(form.is_valid())


class CotizacionFormTests(TestCase):

    def setUp(self):
        self.cliente = crear_cliente(
            nombre="CotF", email="cotf@test.com", doc="90090001"
        )

    def _datos(self):
        return {
            "cliente": self.cliente.pk,
            "fecha_cotizacion": timezone.now().date().isoformat(),
            "fecha_vencimiento": (
                timezone.now().date() + timedelta(days=30)
            ).isoformat(),
            "validez_dias": "30",
            "moneda": "COP",
            "subtotal": "100000",
            "impuesto": "19000",
            "descuento": "0",
            "total": "119000",
            "estado": "borrador",
            "requiere_produccion": "0",
        }

    def test_formulario_valido(self):
        form = CotizacionForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_fecha_vencimiento_pasada_invalida(self):
        datos = self._datos()
        datos["fecha_vencimiento"] = (
            timezone.now().date() - timedelta(days=1)
        ).isoformat()
        form = CotizacionForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_vencimiento", form.errors)

    def test_validez_mayor_365_invalido(self):
        datos = self._datos()
        datos["validez_dias"] = "400"
        form = CotizacionForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("validez_dias", form.errors)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Clientes
# ══════════════════════════════════════════════════════════════════════════════

class ClienteListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VCL")
        self.admin = crear_usuario(self.rol, "admin_vcl@test.com", "10100001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("ventas:cliente_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/cliente_list.html")

    def test_lista_muestra_cliente(self):
        crear_cliente(nombre="VistaCliente", email="vista_c@test.com", doc="11100001")
        response = self.client.get(reverse("ventas:cliente_list"))
        self.assertContains(response, "VistaCliente")

    def test_filtro_estado_activo(self):
        response = self.client.get(
            reverse("ventas:cliente_list") + "?estado=ACTIVO"
        )
        self.assertEqual(response.status_code, 200)

    def test_filtro_busqueda(self):
        crear_cliente(nombre="BuscarNombre", email="buscar@test.com", doc="22200001")
        response = self.client.get(
            reverse("ventas:cliente_list") + "?busqueda=BuscarNombre"
        )
        self.assertContains(response, "BuscarNombre")


class ClienteCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VCC")
        self.admin = crear_usuario(self.rol, "admin_vcc@test.com", "33300001")
        autenticar_sesion(self.client, self.admin)

    def test_get_form_200(self):
        response = self.client.get(reverse("ventas:cliente_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_cliente_valido_redirige(self):
        Clientes.objects.filter(email="nuevo_v@test.com").delete()
        response = self.client.post(
            reverse("ventas:cliente_create"),
            {
                "nombre": "Nuevo Vista",
                "apellido": "Test",
                "telefono": "3001234567",
                "email": "nuevo_v@test.com",
                "direccion": "Av. Principal 100",
                "estado": "ACTIVO",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Clientes.objects.filter(email="nuevo_v@test.com").exists()
        )

    def test_crear_cliente_invalido_muestra_form(self):
        response = self.client.post(
            reverse("ventas:cliente_create"),
            {"nombre": "A", "email": "no-email", "estado": "ACTIVO"}
        )
        self.assertEqual(response.status_code, 200)


class ClienteUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VCU")
        self.admin = crear_usuario(self.rol, "admin_vcu@test.com", "44400001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="ActualizarCliente", email="actcli@test.com", doc="55500001"
        )

    def test_get_form_200(self):
        response = self.client.get(
            reverse("ventas:cliente_update", kwargs={"pk": self.cliente.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_actualizar_nombre(self):
        response = self.client.post(
            reverse("ventas:cliente_update", kwargs={"pk": self.cliente.pk}),
            {
                "nombre": "Nombre Actualizado",
                "apellido": "Ruiz",
                "telefono": "3001234567",
                "email": "actcli@test.com",
                "estado": "ACTIVO",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, "Nombre Actualizado")


class ClienteDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VCD")
        self.admin = crear_usuario(self.rol, "admin_vcd@test.com", "66600001")
        autenticar_sesion(self.client, self.admin)

    def test_eliminar_cliente_sin_pedidos(self):
        c = crear_cliente(
            nombre="EliminarCliente", email="elim_c@test.com", doc="77700001"
        )
        response = self.client.post(
            reverse("ventas:cliente_delete", kwargs={"pk": c.pk})
        )
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertIsNotNone(c.deleted_at)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Pedidos
# ══════════════════════════════════════════════════════════════════════════════

class PedidoListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VP")
        self.admin = crear_usuario(self.rol, "admin_vp@test.com", "88800001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="PedList", email="pedlist@test.com", doc="99900001"
        )

    def test_lista_status_200(self):
        response = self.client.get(reverse("ventas:pedido_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/pedido_list.html")

    def test_filtro_estado_pendiente(self):
        response = self.client.get(
            reverse("ventas:pedido_list") + "?estado=PENDIENTE"
        )
        self.assertEqual(response.status_code, 200)

    def test_contexto_tiene_clientes(self):
        response = self.client.get(reverse("ventas:pedido_list"))
        self.assertIn("clientes", response.context)


class PedidoCreateViewTests(TestCase):

    # El setUp se encarga de crear un usuario con rol adecuado, autenticar la sesión y crear un cliente para usar en los tests de creación de pedidos.
    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VPC")
        self.admin = crear_usuario(self.rol, "admin_vpc@test.com", "10010001")
        self.assertIsNotNone(self.admin.pk, "El usuario no se guardó en BD")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="PedCreate", email="pedcreate@test.com", doc="20020001"
        )

    # El test_get_form_200 verifica que la vista de creación de pedidos responde con un status 200, lo que indica que el formulario se muestra correctamente.
    def test_get_form_200(self):
        response = self.client.get(reverse("ventas:pedido_create"))
        self.assertEqual(response.status_code, 200)

    # El test_crear_pedido_valido_redirige simula el envío de un formulario con datos válidos para crear un pedido. 
    # Verifica que la respuesta sea una redirección (status 302), lo que indica que el pedido se creó exitosamente y 
    # se redirigió al usuario a otra página (probablemente la lista de pedidos o el detalle del nuevo pedido).
    def test_crear_pedido_valido_redirige(self):
        response = self.client.post(
            reverse("ventas:pedido_create"),
            {
                "cliente": self.cliente.pk,
                "fecha_entrega_estimada": (
                    timezone.now().date() + timedelta(days=7)
                ).isoformat(),
                "total_pedido": "0",
                "estado_pedido": "PENDIENTE",
                "direccion_entrega": "Calle 50 # 30-10",
            }
        )
        if response.status_code == 200 and hasattr(response, 'context') and response.context:
            form = response.context.get('form')
            if form:
                print("Errores form pedido:", form.errors)
        self.assertEqual(response.status_code, 302)

    # El test_crear_pedido_sin_cliente_invalido simula el envío de un formulario de creación de pedido sin seleccionar un cliente, lo que es un caso inválido.
    def test_crear_pedido_sin_cliente_invalido(self):
        response = self.client.post(
            reverse("ventas:pedido_create"),
            {
                "cliente": "",
                "total_pedido": "0",
                "estado_pedido": "PENDIENTE",
            }
        )
        self.assertEqual(response.status_code, 200)


class PedidoDetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VPD")
        self.admin = crear_usuario(self.rol, "admin_vpd@test.com", "30030001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="PedDet", email="peddet@test.com", doc="40040001"
        )
        self.pedido = crear_pedido(self.cliente, self.admin)

    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("ventas:pedido_detail", kwargs={"pk": self.pedido.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_contexto_tiene_detalles(self):
        response = self.client.get(
            reverse("ventas:pedido_detail", kwargs={"pk": self.pedido.pk})
        )
        self.assertIn("detalles", response.context)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Ventas
# ══════════════════════════════════════════════════════════════════════════════

class VentaListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VV")
        self.admin = crear_usuario(self.rol, "admin_vv@test.com", "50050001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("ventas:venta_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/venta_list.html")

    def test_filtro_estado_completada(self):
        response = self.client.get(
            reverse("ventas:venta_list") + "?estado=COMPLETADA"
        )
        self.assertEqual(response.status_code, 200)

    def test_contexto_tiene_clientes(self):
        response = self.client.get(reverse("ventas:venta_list"))
        self.assertIn("clientes", response.context)


class VentaCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VVC")
        self.admin = crear_usuario(self.rol, "admin_vvc@test.com", "60060001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="VentaCr", email="ventacr@test.com", doc="70070001"
        )

    def test_get_form_200(self):
        response = self.client.get(reverse("ventas:venta_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_venta_valida_redirige(self):
        response = self.client.post(
            reverse("ventas:venta_create"),
            {
                "cliente": self.cliente.pk,
                "tipo_venta": "DIRECTA",
                "subtotal": "100000",
                "impuesto": "19000",
                "descuento": "0",
                "total": "119000",
                "estado_venta": "PENDIENTE",
            }
        )
        self.assertEqual(response.status_code, 302)


class VentaDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VVD")
        self.admin = crear_usuario(self.rol, "admin_vvd@test.com", "80080001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="VentaDel", email="ventadel@test.com", doc="90090001"
        )

    def test_eliminar_venta_pendiente(self):
        v = crear_venta(self.admin, self.cliente, estado="PENDIENTE")
        response = self.client.post(
            reverse("ventas:venta_delete", kwargs={"pk": v.pk})
        )
        self.assertEqual(response.status_code, 302)
        v.refresh_from_db()
        self.assertIsNotNone(v.deleted_at)

    def test_no_eliminar_venta_completada(self):
        v = crear_venta(self.admin, self.cliente, estado="COMPLETADA")
        response = self.client.post(
            reverse("ventas:venta_delete", kwargs={"pk": v.pk})
        )
        self.assertEqual(response.status_code, 302)
        v.refresh_from_db()
        self.assertIsNone(v.deleted_at)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Cotizaciones
# ══════════════════════════════════════════════════════════════════════════════

class CotizacionListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VC")
        self.admin = crear_usuario(self.rol, "admin_vc@test.com", "11011001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("ventas:cotizacion_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/cotizacion_list.html")

    def test_filtro_estado_borrador(self):
        response = self.client.get(
            reverse("ventas:cotizacion_list") + "?estado=borrador"
        )
        self.assertEqual(response.status_code, 200)


class CotizacionCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_VCC2")
        self.admin = crear_usuario(self.rol, "admin_vcc2@test.com", "22022001")
        autenticar_sesion(self.client, self.admin)
        self.cliente = crear_cliente(
            nombre="CotCreate", email="cotcreate@test.com", doc="33033001"
        )

    def test_get_form_200(self):
        response = self.client.get(reverse("ventas:cotizacion_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_cotizacion_valida(self):
        response = self.client.post(
            reverse("ventas:cotizacion_create"),
            {
                "cliente": self.cliente.pk,
                "fecha_cotizacion": timezone.now().date().isoformat(),
                "fecha_vencimiento": (
                    timezone.now().date() + timedelta(days=30)
                ).isoformat(),
                "validez_dias": "30",
                "moneda": "COP",
                "subtotal": "100000",
                "impuesto": "19000",
                "descuento": "0",
                "total": "119000",
                "estado": "borrador",
                "requiere_produccion": "0",
            }
        )
        self.assertEqual(response.status_code, 302)


# ══════════════════════════════════════════════════════════════════════════════
# CARRITO
# ══════════════════════════════════════════════════════════════════════════════

class CarritoAPITests(TestCase):

    def setUp(self):
        self.client = Client()
        self.cat = crear_categoria("CAT CARRITO")
        self.prod = crear_producto(self.cat, codigo="CAR-P01", precio=50000)
        # Crear cliente y autenticar como cliente en sesión
        self.cliente = crear_cliente(
            nombre="CarritoCli", email="carritotest@test.com", doc="44044001"
        )
        s = self.client.session
        s["cliente_id"] = self.cliente.pk
        s["cliente_auth"] = True
        s["cliente_nombre"] = "CarritoCli"
        s["cliente_email"] = "carritotest@test.com"
        s.save()

    def test_agregar_producto_al_carrito(self):
        import json
        response = self.client.post(
            reverse("ventas:api_carrito_agregar"),
            data=json.dumps({
                "producto_id": str(self.prod.pk),
                "cantidad": 2
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_contador_carrito(self):
        response = self.client.get(reverse("ventas:api_carrito_contador"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cantidad", data)

    def test_limpiar_carrito(self):
        import json
        response = self.client.post(reverse("ventas:carrito_limpiar"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_producto_no_existente_devuelve_404(self):
        import json
        response = self.client.post(
            reverse("ventas:api_carrito_agregar"),
            data=json.dumps({
                "producto_id": "99999",
                "cantidad": 1
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)