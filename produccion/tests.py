"""
Tests unitarios - Módulo Produccion
Nivel: Intermedio
Cubre: Modelos (Produccion, DetalleProduccionPedido),
       Formularios (ProduccionForm),
       Vistas CRUD (lista, crear, editar, eliminar, detalle)
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Model

from produccion.models import Produccion, DetalleProduccionPedido
from produccion.forms import ProduccionForm
from inventario.models import Producto, Categorias, Proveedores
from ventas.models import Clientes, Pedido
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


def crear_categoria(nombre="CAT PROD"):
    Categorias.objects.filter(nombre_categoria=nombre).delete()
    c = Categorias(
        nombre_categoria=nombre, estado_categoria="activo",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    c.save()
    return c


def crear_producto(categoria, codigo="PRPROD-001"):
    Producto.objects.filter(codigo_producto=codigo).delete()
    p = Producto(
        codigo_producto=codigo,
        referencia_producto="Producto produccion test",
        categoria=categoria,
        precio_actual=Decimal("100000"),
        estado="DISPONIBLE",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(p)
    return p


def crear_proveedor(nombre="Prov Prod"):
    Proveedores.objects.filter(nombre=nombre).delete()
    p = Proveedores(
        nombre=nombre, estado="ACTIVO",
        email=f"{nombre.lower().replace(' ', '_')}@test.com",
        telefono="3001234567",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    p.save()
    return p


def crear_produccion(producto, cantidad=10, estado="PENDIENTE",
                     fecha_inicio=None, proveedor=None):
    fecha_inicio = fecha_inicio or date.today()
    p = Produccion(
        producto=producto,
        cantidad_producida=cantidad,
        estado_produccion=estado,
        fecha_inicio=fecha_inicio,
        proveedor=proveedor,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(p)
    return p


def crear_cliente(nombre="ClienteProd", email="cliprod@test.com", doc="10101001"):
    Clientes.objects.filter(email=email).delete()
    Clientes.objects.filter(documento=doc).delete()
    c = Clientes(
        nombre=nombre, email=email, documento=doc,
        contrasena_cliente=make_password("Cliente123"),
        estado="ACTIVO",
        created_at=timezone.now(), updated_at=timezone.now(),
        fecha_registro=timezone.now(),
    )
    Model.save(c)
    return c


def crear_pedido(cliente, usuario):
    p = Pedido(
        cliente=cliente, usuario=usuario,
        estado_pedido="PENDIENTE",
        total_pedido=Decimal("0"),
        fecha_pedido=timezone.now(),
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    Model.save(p)
    return p


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Produccion
# ══════════════════════════════════════════════════════════════════════════════

class ProduccionModelTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria()
        self.prod = crear_producto(self.cat)

    # ── Creación ──────────────────────────────────────────────────────────────
    def test_crear_produccion_exitosa(self):
        p = crear_produccion(self.prod)
        self.assertIsNotNone(p.pk)
        self.assertEqual(p.estado_produccion, "PENDIENTE")

    def test_str_incluye_codigo_y_estado(self):
        p = crear_produccion(self.prod)
        resultado = str(p)
        self.assertIn(self.prod.codigo_producto, resultado)
        self.assertIn("PENDIENTE", resultado)

    def test_timestamps_generados(self):
        p = crear_produccion(self.prod)
        self.assertIsNotNone(p.created_at)
        self.assertIsNotNone(p.updated_at)

    # ── Métodos de negocio ────────────────────────────────────────────────────
    def test_puede_modificarse_pendiente(self):
        p = crear_produccion(self.prod, estado="PENDIENTE")
        self.assertTrue(p.puede_modificarse())

    def test_puede_modificarse_en_proceso(self):
        p = crear_produccion(self.prod, estado="EN PROCESO")
        self.assertTrue(p.puede_modificarse())

    def test_no_puede_modificarse_terminada(self):
        p = crear_produccion(self.prod, estado="TERMINADA")
        self.assertFalse(p.puede_modificarse())

    def test_no_puede_modificarse_cancelada(self):
        p = crear_produccion(self.prod, estado="CANCELADA")
        self.assertFalse(p.puede_modificarse())

    def test_puede_eliminarse_pendiente_sin_asignaciones(self):
        p = crear_produccion(self.prod, estado="PENDIENTE")
        self.assertTrue(p.puede_eliminarse())

    def test_no_puede_eliminarse_en_proceso(self):
        p = crear_produccion(self.prod, estado="EN PROCESO")
        self.assertFalse(p.puede_eliminarse())

    # ── Cantidades asignadas ──────────────────────────────────────────────────
    def test_get_cantidad_asignada_sin_detalle(self):
        p = crear_produccion(self.prod)
        self.assertEqual(p.get_cantidad_asignada(), 0)

    def test_get_cantidad_disponible_completa(self):
        p = crear_produccion(self.prod, cantidad=20)
        self.assertEqual(p.get_cantidad_disponible(), 20)

    def test_esta_completamente_asignada_false(self):
        p = crear_produccion(self.prod, cantidad=10)
        self.assertFalse(p.esta_completamente_asignada())

    # ── Cambio de estado ──────────────────────────────────────────────────────
    def test_cambiar_estado_pendiente_a_en_proceso(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=5,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        p.save()
        p.cambiar_estado("EN PROCESO")
        self.assertEqual(p.estado_produccion, "EN PROCESO")

    def test_cambiar_estado_pendiente_a_cancelada(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=5,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        p.save()
        p.cambiar_estado("CANCELADA")
        self.assertEqual(p.estado_produccion, "CANCELADA")

    def test_cambiar_estado_invalido_falla(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=5,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        p.save()
        with self.assertRaises(ValidationError):
            p.cambiar_estado("TERMINADA")

    def test_cambiar_estado_terminada_registra_fecha_fin(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=5,
            estado_produccion="EN PROCESO",
            fecha_inicio=date.today(),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        p.save()
        p.cambiar_estado("TERMINADA")
        self.assertIsNotNone(p.fecha_fin)

    # ── Soft delete ───────────────────────────────────────────────────────────
    def test_soft_delete(self):
        p = crear_produccion(self.prod, estado="PENDIENTE")
        pk = p.pk
        p.delete()
        self.assertIsNotNone(p.deleted_at)
        self.assertTrue(Produccion.objects.filter(pk=pk).exists())

    def test_hard_delete(self):
        p = crear_produccion(self.prod, estado="PENDIENTE")
        pk = p.pk
        p.hard_delete()
        self.assertFalse(Produccion.objects.filter(pk=pk).exists())

    # ── Validaciones del modelo ───────────────────────────────────────────────
    def test_cantidad_cero_falla(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=0,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_fecha_fin_anterior_a_inicio_falla(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=5,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
            fecha_fin=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_cantidad_positiva_valida(self):
        p = Produccion(
            producto=self.prod,
            cantidad_producida=100,
            estado_produccion="PENDIENTE",
            fecha_inicio=date.today(),
        )
        # No lanza excepcion
        p.full_clean()


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: DetalleProduccionPedido
# ══════════════════════════════════════════════════════════════════════════════

class DetalleProduccionPedidoModelTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT DPP")
        self.prod = crear_producto(self.cat, codigo="DPP-001")
        self.rol = crear_rol("ROL_DPP")
        self.usuario = crear_usuario(self.rol, "udpp@test.com", "20202001")
        self.cliente = crear_cliente()
        self.pedido = crear_pedido(self.cliente, self.usuario)
        self.produccion = crear_produccion(self.prod, cantidad=20)

    def test_crear_detalle_exitoso(self):
        d = DetalleProduccionPedido(
            produccion=self.produccion,
            pedido=self.pedido,
            producto=self.prod,
            cantidad_asignada=Decimal("5"),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        Model.save(d)
        self.assertIsNotNone(d.pk)
        self.assertEqual(d.cantidad_asignada, Decimal("5"))

    def test_cantidad_asignada_excede_disponible_falla(self):
        d = DetalleProduccionPedido(
            produccion=self.produccion,
            pedido=self.pedido,
            producto=self.prod,
            cantidad_asignada=Decimal("999"),
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_cantidad_cero_falla(self):
        d = DetalleProduccionPedido(
            produccion=self.produccion,
            pedido=self.pedido,
            producto=self.prod,
            cantidad_asignada=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_soft_delete(self):
        d = DetalleProduccionPedido(
            produccion=self.produccion,
            pedido=self.pedido,
            producto=self.prod,
            cantidad_asignada=Decimal("3"),
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        Model.save(d)
        pk = d.pk
        d.delete()
        self.assertIsNotNone(d.deleted_at)
        self.assertTrue(DetalleProduccionPedido.objects.filter(pk=pk).exists())


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIO: ProduccionForm
# ══════════════════════════════════════════════════════════════════════════════

class ProduccionFormTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT FORM PROD")
        self.prod = crear_producto(self.cat, codigo="FP-001")

    def _datos(self, cantidad=10, estado="PENDIENTE", fecha_inicio=None,
               fecha_fin=None):
        datos = {
            "producto": self.prod.pk,
            "cantidad_producida": str(cantidad),
            "estado_produccion": estado,
            "fecha_inicio": fecha_inicio or date.today().isoformat(),
        }
        if fecha_fin:
            datos["fecha_fin"] = fecha_fin
        return datos

    def test_formulario_valido(self):
        form = ProduccionForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_cantidad_cero_invalida(self):
        form = ProduccionForm(data=self._datos(cantidad=0))
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad_producida", form.errors)

    def test_cantidad_negativa_invalida(self):
        form = ProduccionForm(data=self._datos(cantidad=-5))
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad_producida", form.errors)

    def test_fecha_fin_anterior_a_inicio_invalida(self):
        form = ProduccionForm(data=self._datos(
            fecha_inicio=date.today().isoformat(),
            fecha_fin=(date.today() - timedelta(days=2)).isoformat()
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_fin", form.errors)

    def test_estado_terminada_requiere_fecha_fin(self):
        form = ProduccionForm(data=self._datos(estado="TERMINADA"))
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_fin", form.errors)

    def test_estado_terminada_con_fecha_fin_valido(self):
        form = ProduccionForm(data=self._datos(
            estado="TERMINADA",
            fecha_fin=date.today().isoformat()
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_producto_invalido(self):
        datos = self._datos()
        datos["producto"] = ""
        form = ProduccionForm(data=datos)
        self.assertFalse(form.is_valid())

    def test_cantidad_muy_grande_invalida(self):
        form = ProduccionForm(data=self._datos(cantidad=1000001))
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad_producida", form.errors)

    def test_estado_en_proceso_valido(self):
        form = ProduccionForm(data=self._datos(estado="EN PROCESO"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_estado_cancelada_valido(self):
        form = ProduccionForm(data=self._datos(estado="CANCELADA"))
        self.assertTrue(form.is_valid(), form.errors)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Produccion
# ══════════════════════════════════════════════════════════════════════════════

class ProduccionListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PL")
        self.admin = crear_usuario(self.rol, "admin_pl@test.com", "30303001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT PL")
        self.prod = crear_producto(self.cat, codigo="PL-001")

    def test_lista_status_200(self):
        response = self.client.get(reverse("produccion:produccion_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produccion/produccion_list.html")

    def test_lista_muestra_produccion(self):
        crear_produccion(self.prod, cantidad=15)
        response = self.client.get(reverse("produccion:produccion_list"))
        self.assertContains(response, self.prod.codigo_producto)

    def test_filtro_por_estado_pendiente(self):
        crear_produccion(self.prod, estado="PENDIENTE")
        response = self.client.get(
            reverse("produccion:produccion_list") + "?estado=PENDIENTE"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.prod.codigo_producto)

    def test_filtro_por_estado_en_proceso(self):
        crear_produccion(self.prod, estado="EN PROCESO")
        response = self.client.get(
            reverse("produccion:produccion_list") + "?estado=EN PROCESO"
        )
        self.assertEqual(response.status_code, 200)

    def test_filtro_por_producto(self):
        crear_produccion(self.prod)
        response = self.client.get(
            reverse("produccion:produccion_list") + f"?producto={self.prod.pk}"
        )
        self.assertContains(response, self.prod.codigo_producto)

    def test_filtro_busqueda_por_codigo(self):
        crear_produccion(self.prod)
        response = self.client.get(
            reverse("produccion:produccion_list") + f"?busqueda={self.prod.codigo_producto}"
        )
        self.assertContains(response, self.prod.codigo_producto)

    def test_contexto_tiene_productos(self):
        response = self.client.get(reverse("produccion:produccion_list"))
        self.assertIn("productos", response.context)

    def test_contexto_tiene_estados(self):
        response = self.client.get(reverse("produccion:produccion_list"))
        self.assertIn("estados", response.context)
        self.assertIn("PENDIENTE", response.context["estados"])

    def test_paginacion_activa(self):
        for i in range(12):
            cat = crear_categoria(f"CAT PAG {i}")
            prod = crear_producto(cat, codigo=f"PAG-{i:03d}")
            crear_produccion(prod, cantidad=i + 1)
        response = self.client.get(reverse("produccion:produccion_list"))
        self.assertEqual(response.status_code, 200)


class ProduccionCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PC2")
        self.admin = crear_usuario(self.rol, "admin_pc2@test.com", "40404001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT PC2")
        self.prod = crear_producto(self.cat, codigo="PC2-001")

    def test_get_form_status_200(self):
        response = self.client.get(reverse("produccion:produccion_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produccion/produccion_form.html")

    def test_contexto_tiene_titulo(self):
        response = self.client.get(reverse("produccion:produccion_create"))
        self.assertIn("titulo", response.context)
        self.assertEqual(response.context["titulo"], "Nueva Producción")

    def test_crear_produccion_valida_redirige(self):
        response = self.client.post(
            reverse("produccion:produccion_create"),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "25",
                "estado_produccion": "PENDIENTE",
                "fecha_inicio": date.today().isoformat(),
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Produccion.objects.filter(
                producto=self.prod, deleted_at__isnull=True
            ).exists()
        )

    def test_crear_produccion_invalida_muestra_form(self):
        response = self.client.post(
            reverse("produccion:produccion_create"),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "0",
                "estado_produccion": "PENDIENTE",
                "fecha_inicio": date.today().isoformat(),
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_crear_sin_producto_invalido(self):
        response = self.client.post(
            reverse("produccion:produccion_create"),
            {
                "producto": "",
                "cantidad_producida": "10",
                "estado_produccion": "PENDIENTE",
                "fecha_inicio": date.today().isoformat(),
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_crear_con_fecha_fin_anterior_invalido(self):
        response = self.client.post(
            reverse("produccion:produccion_create"),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "10",
                "estado_produccion": "PENDIENTE",
                "fecha_inicio": date.today().isoformat(),
                "fecha_fin": (date.today() - timedelta(days=3)).isoformat(),
            }
        )
        self.assertEqual(response.status_code, 200)


class ProduccionUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PU2")
        self.admin = crear_usuario(self.rol, "admin_pu2@test.com", "50505001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT PU2")
        self.prod = crear_producto(self.cat, codigo="PU2-001")
        self.produccion = crear_produccion(self.prod, cantidad=10)

    def test_get_form_status_200(self):
        response = self.client.get(
            reverse("produccion:produccion_update", kwargs={"pk": self.produccion.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produccion/produccion_form.html")

    def test_contexto_tiene_titulo(self):
        response = self.client.get(
            reverse("produccion:produccion_update", kwargs={"pk": self.produccion.pk})
        )
        self.assertIn("titulo", response.context)
        self.assertEqual(response.context["titulo"], "Editar Producción")

    def test_actualizar_cantidad_exitoso(self):
        response = self.client.post(
            reverse("produccion:produccion_update", kwargs={"pk": self.produccion.pk}),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "50",
                "estado_produccion": "PENDIENTE",
                "fecha_inicio": date.today().isoformat(),
            }
        )
        self.assertEqual(response.status_code, 302)
        self.produccion.refresh_from_db()
        self.assertEqual(self.produccion.cantidad_producida, 50)

    def test_actualizar_estado_a_en_proceso(self):
        response = self.client.post(
            reverse("produccion:produccion_update", kwargs={"pk": self.produccion.pk}),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "10",
                "estado_produccion": "EN PROCESO",
                "fecha_inicio": date.today().isoformat(),
            }
        )
        self.assertEqual(response.status_code, 302)
        self.produccion.refresh_from_db()
        self.assertEqual(self.produccion.estado_produccion, "EN PROCESO")

    def test_no_editar_produccion_terminada(self):
        prod_term = crear_produccion(
            self.prod, cantidad=5, estado="TERMINADA",
            fecha_inicio=date.today() - timedelta(days=2)
        )
        response = self.client.post(
            reverse("produccion:produccion_update", kwargs={"pk": prod_term.pk}),
            {
                "producto": self.prod.pk,
                "cantidad_producida": "999",
                "estado_produccion": "TERMINADA",
                "fecha_inicio": (date.today() - timedelta(days=2)).isoformat(),
                "fecha_fin": date.today().isoformat(),
            }
        )
        # Redirige con mensaje de error, no guarda
        self.assertEqual(response.status_code, 302)
        prod_term.refresh_from_db()
        self.assertNotEqual(prod_term.cantidad_producida, 999)


class ProduccionDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PD2")
        self.admin = crear_usuario(self.rol, "admin_pd2@test.com", "60606001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT PD2")
        self.prod = crear_producto(self.cat, codigo="PD2-001")

    def test_eliminar_produccion_pendiente(self):
        p = crear_produccion(self.prod, estado="PENDIENTE")
        response = self.client.post(
            reverse("produccion:produccion_delete", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertIsNotNone(p.deleted_at)

    def test_no_eliminar_produccion_en_proceso(self):
        p = crear_produccion(self.prod, estado="EN PROCESO")
        response = self.client.post(
            reverse("produccion:produccion_delete", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertIsNone(p.deleted_at)

    def test_no_eliminar_produccion_terminada(self):
        p = crear_produccion(self.prod, estado="TERMINADA")
        response = self.client.post(
            reverse("produccion:produccion_delete", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertIsNone(p.deleted_at)

    def test_produccion_no_aparece_en_lista_tras_eliminar(self):
        cat2 = crear_categoria("CAT PD2 B")
        prod2 = crear_producto(cat2, codigo="PD2-002")
        p = crear_produccion(prod2, estado="PENDIENTE")
        self.client.post(
            reverse("produccion:produccion_delete", kwargs={"pk": p.pk})
        )
        response = self.client.get(reverse("produccion:produccion_list"))
        # El producto no aparece porque la produccion fue eliminada
        self.assertEqual(response.status_code, 200)


class ProduccionDetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PDV")
        self.admin = crear_usuario(self.rol, "admin_pdv@test.com", "70707001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT PDV")
        self.prod = crear_producto(self.cat, codigo="PDV-001")
        self.produccion = crear_produccion(self.prod, cantidad=20)

    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "produccion/produccion_detail.html")

    def test_detalle_muestra_codigo_producto(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertContains(response, self.prod.codigo_producto)

    def test_contexto_tiene_cantidad_asignada(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertIn("cantidad_asignada", response.context)

    def test_contexto_tiene_cantidad_disponible(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertIn("cantidad_disponible", response.context)
        self.assertEqual(response.context["cantidad_disponible"], 20)

    def test_contexto_tiene_detalles(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertIn("detalles", response.context)

    def test_contexto_esta_completamente_asignada(self):
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": self.produccion.pk})
        )
        self.assertIn("esta_completamente_asignada", response.context)
        self.assertFalse(response.context["esta_completamente_asignada"])

    def test_produccion_eliminada_devuelve_404(self):
        p = crear_produccion(self.prod, cantidad=5)
        p.delete()
        response = self.client.get(
            reverse("produccion:produccion_detail", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 404)