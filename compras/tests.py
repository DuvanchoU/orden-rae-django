"""
Tests unitarios - Módulo Compras
Nivel: Intermedio
Cubre: Modelos (Compras, DetalleCompra), Formularios (CompraForm, DetalleCompraForm),
       Vistas CRUD (lista, crear, editar, eliminar, detalle, recibir, cancelar)
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Model

from compras.models import Compras, DetalleCompra
from inventario.models import Producto, Categorias, Proveedores, Bodegas, Inventario
from usuarios.models import RolesOld, Usuarios
from django.contrib.auth.hashers import make_password


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def crear_rol(nombre="GERENTE"):
    RolesOld.objects.filter(nombre_rol=nombre).delete()
    r = RolesOld(nombre_rol=nombre, descripcion="Rol prueba")
    r.save()
    return r


def crear_usuario(rol, correo="admin@test.com", doc="00000001"):
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
    Model.save(u)
    return u


def autenticar_sesion(client, usuario):
    s = client.session
    s["usuario_id"] = usuario.pk
    s["usuario_nombre"] = usuario.get_full_name()
    s["usuario_rol"] = usuario.id_rol.nombre_rol
    s.save()


def crear_proveedor(nombre="Prov Compras", estado="ACTIVO"):
    Proveedores.objects.filter(nombre=nombre).delete()
    p = Proveedores(
        nombre=nombre, estado=estado,
        email=f"{nombre.lower().replace(' ', '_')}@test.com",
        telefono="3001234567",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    p.save()
    return p


def crear_categoria(nombre="CAT C"):
    Categorias.objects.filter(nombre_categoria=nombre).delete()
    c = Categorias(
        nombre_categoria=nombre, estado_categoria="activo",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    c.save()
    return c


def crear_producto(categoria, codigo="CPROD-001", precio=100000):
    Producto.objects.filter(codigo_producto=codigo).delete()
    p = Producto(
        codigo_producto=codigo,
        referencia_producto="Producto compra test",
        categoria=categoria,
        precio_actual=Decimal(str(precio)),
        estado="DISPONIBLE",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(p)
    return p


def crear_compra(proveedor, usuario=None, estado="PENDIENTE"):
    c = Compras(
        proveedor=proveedor,
        usuario=usuario,
        fecha_compra=timezone.now().date(),
        total_compra=Decimal("0"),
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(c)
    return c


def crear_detalle(compra, producto, cantidad=5, precio=10000):
    d = DetalleCompra(
        compra=compra,
        producto=producto,
        cantidad=cantidad,
        precio_unitario=Decimal(str(precio)),
        subtotal=Decimal(str(cantidad * precio)),
    )
    Model.save(d)
    return d


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Compras
# ══════════════════════════════════════════════════════════════════════════════

class ComprasModelTests(TestCase):

    def setUp(self):
        self.prov = crear_proveedor()
        self.rol = crear_rol()
        self.usuario = crear_usuario(self.rol)

    # ── Creación ──────────────────────────────────────────────────────────────
    def test_crear_compra_exitoso(self):
        c = crear_compra(self.prov, self.usuario)
        self.assertIsNotNone(c.pk)
        self.assertEqual(c.estado, "PENDIENTE")

    def test_str_incluye_id_y_proveedor(self):
        c = crear_compra(self.prov, self.usuario)
        resultado = str(c)
        self.assertIn(str(c.id_compra), resultado)
        self.assertIn(self.prov.nombre, resultado)

    # ── Métodos de negocio ────────────────────────────────────────────────────
    def test_puede_modificarse_pendiente(self):
        c = crear_compra(self.prov, self.usuario, estado="PENDIENTE")
        self.assertTrue(c.puede_modificarse())

    def test_no_puede_modificarse_recibida(self):
        c = crear_compra(self.prov, self.usuario, estado="RECIBIDA")
        self.assertFalse(c.puede_modificarse())

    def test_no_puede_modificarse_cancelada(self):
        c = crear_compra(self.prov, self.usuario, estado="CANCELADA")
        self.assertFalse(c.puede_modificarse())

    def test_puede_eliminarse_pendiente(self):
        c = crear_compra(self.prov, self.usuario, estado="PENDIENTE")
        self.assertTrue(c.puede_eliminarse())

    def test_no_puede_eliminarse_recibida(self):
        c = crear_compra(self.prov, self.usuario, estado="RECIBIDA")
        self.assertFalse(c.puede_eliminarse())

    def test_puede_recibirse_con_detalles(self):
        c = crear_compra(self.prov, self.usuario)
        cat = crear_categoria()
        prod = crear_producto(cat)
        crear_detalle(c, prod)
        self.assertTrue(c.puede_recibirse())

    def test_no_puede_recibirse_sin_detalles(self):
        c = crear_compra(self.prov, self.usuario)
        self.assertFalse(c.puede_recibirse())

    def test_no_puede_recibirse_ya_recibida(self):
        c = crear_compra(self.prov, self.usuario, estado="RECIBIDA")
        self.assertFalse(c.puede_recibirse())

    # ── Cancelar ──────────────────────────────────────────────────────────────
    def test_cancelar_compra_pendiente(self):
        c = crear_compra(self.prov, self.usuario)
        c.cancelar_compra()
        self.assertEqual(c.estado, "CANCELADA")

    def test_cancelar_compra_no_pendiente_falla(self):
        c = crear_compra(self.prov, self.usuario, estado="RECIBIDA")
        with self.assertRaises(ValidationError):
            c.cancelar_compra()

    # ── Soft delete ───────────────────────────────────────────────────────────
    def test_soft_delete_pendiente(self):
        c = crear_compra(self.prov, self.usuario)
        c.delete()
        self.assertIsNotNone(c.deleted_at)
        self.assertTrue(Compras.objects.filter(pk=c.pk).exists())

    def test_soft_delete_no_pendiente_falla(self):
        c = crear_compra(self.prov, self.usuario, estado="RECIBIDA")
        with self.assertRaises(ValidationError):
            c.delete()

    # ── Total formateado ──────────────────────────────────────────────────────
    def test_get_total_formateado(self):
        c = crear_compra(self.prov, self.usuario)
        c.total_compra = Decimal("1500000")
        Model.save(c)
        fmt = c.get_total_formateado()
        self.assertIn("1.500.000", fmt)

    # ── Cantidad de productos ─────────────────────────────────────────────────
    def test_get_cantidad_productos_cero_sin_detalles(self):
        c = crear_compra(self.prov, self.usuario)
        self.assertEqual(c.get_cantidad_productos(), 0)

    def test_get_cantidad_productos_con_detalles(self):
        c = crear_compra(self.prov, self.usuario)
        cat = crear_categoria("CAT QTY")
        prod = crear_producto(cat, codigo="QTY-001")
        crear_detalle(c, prod, cantidad=7)
        self.assertEqual(c.get_cantidad_productos(), 7)


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: DetalleCompra
# ══════════════════════════════════════════════════════════════════════════════

class DetalleCompraModelTests(TestCase):

    def setUp(self):
        self.prov = crear_proveedor("Prov Det")
        self.rol = crear_rol("ROL_DET")
        self.usuario = crear_usuario(self.rol, "det@test.com", "10000001")
        self.compra = crear_compra(self.prov, self.usuario)
        self.cat = crear_categoria("CAT DET")
        self.prod = crear_producto(self.cat, codigo="DET-C01")

    def test_crear_detalle_exitoso(self):
        d = crear_detalle(self.compra, self.prod, cantidad=3, precio=50000)
        self.assertIsNotNone(d.pk)
        self.assertEqual(d.cantidad, 3)
        self.assertEqual(d.precio_unitario, Decimal("50000"))

    def test_subtotal_calculado_correctamente(self):
        d = crear_detalle(self.compra, self.prod, cantidad=4, precio=25000)
        self.assertEqual(d.subtotal, Decimal("100000"))

    def test_str_incluye_codigo_y_cantidad(self):
        d = crear_detalle(self.compra, self.prod, cantidad=2)
        resultado = str(d)
        self.assertIn(self.prod.codigo_producto, resultado)
        self.assertIn("2", resultado)

    def test_subtotal_formateado(self):
        d = crear_detalle(self.compra, self.prod, cantidad=2, precio=500000)
        fmt = d.get_subtotal_formateado()
        self.assertIn("1.000.000", fmt)

    def test_precio_unitario_formateado(self):
        d = crear_detalle(self.compra, self.prod, cantidad=1, precio=250000)
        fmt = d.get_precio_unitario_formateado()
        self.assertIn("250.000", fmt)


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIOS
# ══════════════════════════════════════════════════════════════════════════════

class CompraFormTests(TestCase):

    def setUp(self):
        self.prov = crear_proveedor("Prov Form")

    def _datos(self):
        return {
            "proveedor": self.prov.pk,
            "fecha_compra": timezone.now().date().isoformat(),
            "total_compra": "0",
            "estado": "PENDIENTE",
        }

    def test_formulario_valido(self):
        from compras.forms import CompraForm
        form = CompraForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_fecha_futura_invalida(self):
        from compras.forms import CompraForm
        from datetime import date, timedelta
        datos = self._datos()
        datos["fecha_compra"] = (date.today() + timedelta(days=5)).isoformat()
        form = CompraForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_compra", form.errors)

    def test_sin_proveedor_invalido(self):
        from compras.forms import CompraForm
        datos = self._datos()
        datos["proveedor"] = ""
        form = CompraForm(data=datos)
        self.assertFalse(form.is_valid())

    def test_proveedor_inactivo_invalido(self):
        from compras.forms import CompraForm
        prov_inact = crear_proveedor("Prov Inact Form", estado="INACTIVO")
        datos = self._datos()
        datos["proveedor"] = prov_inact.pk
        form = CompraForm(data=datos)
        # El proveedor inactivo no aparece en el queryset del form
        self.assertFalse(form.is_valid())


class DetalleCompraFormTests(TestCase):

    def setUp(self):
        self.prov = crear_proveedor("Prov DForm")
        self.rol = crear_rol("ROL_DF")
        self.usuario = crear_usuario(self.rol, "dform@test.com", "20000001")
        self.compra = crear_compra(self.prov, self.usuario)
        self.cat = crear_categoria("CAT DF")
        self.prod = crear_producto(self.cat, codigo="DF-P01")

    def _datos(self):
        return {
            "compra": self.compra.pk,
            "producto": self.prod.pk,
            "cantidad": "5",
            "precio_unitario": "50000",
        }

    def test_formulario_valido(self):
        from compras.forms import DetalleCompraForm
        form = DetalleCompraForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_cantidad_cero_invalida(self):
        from compras.forms import DetalleCompraForm
        datos = self._datos()
        datos["cantidad"] = "0"
        form = DetalleCompraForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)

    def test_cantidad_negativa_invalida(self):
        from compras.forms import DetalleCompraForm
        datos = self._datos()
        datos["cantidad"] = "-3"
        form = DetalleCompraForm(data=datos)
        self.assertFalse(form.is_valid())

    def test_precio_negativo_invalido(self):
        from compras.forms import DetalleCompraForm
        datos = self._datos()
        datos["precio_unitario"] = "-1000"
        form = DetalleCompraForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_unitario", form.errors)

    def test_producto_duplicado_en_misma_compra_invalido(self):
        from compras.forms import DetalleCompraForm
        crear_detalle(self.compra, self.prod)
        form = DetalleCompraForm(data=self._datos())
        self.assertFalse(form.is_valid())


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS
# ══════════════════════════════════════════════════════════════════════════════

class CompraListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CL")
        self.admin = crear_usuario(self.rol, "admin_cl@test.com", "30000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Lista")

    def test_lista_status_200(self):
        response = self.client.get(reverse("compras:compra_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compras/compra_list.html")

    def test_lista_muestra_compras(self):
        crear_compra(self.prov, self.admin)
        response = self.client.get(reverse("compras:compra_list"))
        self.assertContains(response, self.prov.nombre)

    def test_filtro_por_estado_pendiente(self):
        crear_compra(self.prov, self.admin, estado="PENDIENTE")
        response = self.client.get(
            reverse("compras:compra_list") + "?estado=PENDIENTE"
        )
        self.assertEqual(response.status_code, 200)

    def test_filtro_por_proveedor(self):
        crear_compra(self.prov, self.admin)
        response = self.client.get(
            reverse("compras:compra_list") + f"?proveedor={self.prov.pk}"
        )
        self.assertContains(response, self.prov.nombre)

    def test_contexto_tiene_proveedores(self):
        response = self.client.get(reverse("compras:compra_list"))
        self.assertIn("proveedores", response.context)

    def test_contexto_tiene_estados(self):
        response = self.client.get(reverse("compras:compra_list"))
        self.assertIn("estados", response.context)


class CompraCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CC")
        self.admin = crear_usuario(self.rol, "admin_cc@test.com", "40000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Create")

    def test_get_form_status_200(self):
        response = self.client.get(reverse("compras:compra_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compras/compra_form.html")

    def test_crear_compra_valida_redirige(self):
        response = self.client.post(
            reverse("compras:compra_create"),
            {
                "proveedor": self.prov.pk,
                "fecha_compra": timezone.now().date().isoformat(),
                "total_compra": "0",
                "estado": "PENDIENTE",
            }
        )
        # Redirige al detalle de la compra creada
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Compras.objects.filter(
                proveedor=self.prov, deleted_at__isnull=True
            ).exists()
        )

    def test_crear_compra_sin_proveedor_invalido(self):
        response = self.client.post(
            reverse("compras:compra_create"),
            {
                "proveedor": "",
                "fecha_compra": timezone.now().date().isoformat(),
                "total_compra": "0",
            }
        )
        self.assertEqual(response.status_code, 200)


class CompraDetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CDV")
        self.admin = crear_usuario(self.rol, "admin_cdv@test.com", "50000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Detail")
        self.compra = crear_compra(self.prov, self.admin)

    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("compras:compra_detail", kwargs={"pk": self.compra.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compras/compra_detail.html")

    def test_detalle_muestra_proveedor(self):
        response = self.client.get(
            reverse("compras:compra_detail", kwargs={"pk": self.compra.pk})
        )
        self.assertContains(response, self.prov.nombre)

    def test_contexto_tiene_detalles(self):
        response = self.client.get(
            reverse("compras:compra_detail", kwargs={"pk": self.compra.pk})
        )
        self.assertIn("detalles", response.context)

    def test_contexto_puede_modificarse(self):
        response = self.client.get(
            reverse("compras:compra_detail", kwargs={"pk": self.compra.pk})
        )
        self.assertTrue(response.context["puede_modificarse"])


class CompraUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CU")
        self.admin = crear_usuario(self.rol, "admin_cu@test.com", "60000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Update")
        self.compra = crear_compra(self.prov, self.admin)

    def test_get_form_status_200(self):
        response = self.client.get(
            reverse("compras:compra_update", kwargs={"pk": self.compra.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_editar_compra_pendiente_redirige(self):
        response = self.client.post(
            reverse("compras:compra_update", kwargs={"pk": self.compra.pk}),
            {
                "proveedor": self.prov.pk,
                "fecha_compra": timezone.now().date().isoformat(),
                "total_compra": "500000",
                "estado": "PENDIENTE",
            }
        )
        self.assertEqual(response.status_code, 302)

    def test_no_editar_compra_recibida(self):
        compra_rec = crear_compra(self.prov, self.admin, estado="RECIBIDA")
        response = self.client.post(
            reverse("compras:compra_update", kwargs={"pk": compra_rec.pk}),
            {
                "proveedor": self.prov.pk,
                "fecha_compra": timezone.now().date().isoformat(),
                "total_compra": "999999",
                "estado": "RECIBIDA",
            }
        )
        # No puede modificarse, redirige con error
        self.assertEqual(response.status_code, 302)


class CompraDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CD")
        self.admin = crear_usuario(self.rol, "admin_cd@test.com", "70000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Delete")

    def test_eliminar_compra_pendiente(self):
        c = crear_compra(self.prov, self.admin, estado="PENDIENTE")
        response = self.client.post(
            reverse("compras:compra_delete", kwargs={"pk": c.pk})
        )
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertIsNotNone(c.deleted_at)

    def test_no_eliminar_compra_recibida(self):
        c = crear_compra(self.prov, self.admin, estado="RECIBIDA")
        response = self.client.post(
            reverse("compras:compra_delete", kwargs={"pk": c.pk})
        )
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertIsNone(c.deleted_at)


class CompraCancelarViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CCAN")
        self.admin = crear_usuario(self.rol, "admin_ccan@test.com", "80000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov Cancel")

    def test_cancelar_compra_pendiente(self):
        c = crear_compra(self.prov, self.admin, estado="PENDIENTE")
        response = self.client.post(
            reverse("compras:compra_cancelar", kwargs={"pk": c.pk})
        )
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.estado, "CANCELADA")

    def test_no_cancelar_compra_ya_cancelada(self):
        c = crear_compra(self.prov, self.admin, estado="CANCELADA")
        response = self.client.post(
            reverse("compras:compra_cancelar", kwargs={"pk": c.pk})
        )
        self.assertEqual(response.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.estado, "CANCELADA")


class DetalleCompraDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_DD")
        self.admin = crear_usuario(self.rol, "admin_dd@test.com", "90000001")
        autenticar_sesion(self.client, self.admin)
        self.prov = crear_proveedor("Prov DetDel")
        self.compra = crear_compra(self.prov, self.admin)
        self.cat = crear_categoria("CAT DD")
        self.prod = crear_producto(self.cat, codigo="DD-P01")

    def test_eliminar_detalle_exitoso(self):
        det = crear_detalle(self.compra, self.prod)
        response = self.client.post(
            reverse("compras:detalle_compra_delete", kwargs={"pk": det.pk})
        )
        self.assertEqual(response.status_code, 302)