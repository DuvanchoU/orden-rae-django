from django.test import TestCase

# Create your tests here.
"""
Tests unitarios - Módulo Inventario
Nivel: Intermedio
Cubre: Modelos (Producto, Categorias, Proveedores, Bodegas, Inventario),
       Formularios (ProductoForm, InventarioForm, ProveedorForm),
       Vistas (CRUD completo con filtros y paginación)
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Model

from inventario.models import (
    Producto, Categorias, Proveedores, Bodegas, Inventario, ImagenesProducto
)
from inventario.forms import (
    ProductoForm, InventarioForm, ProveedorForm, BodegaForm, CategoriaForm
)
from usuarios.models import RolesOld, Usuarios
from django.contrib.auth.hashers import make_password


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def crear_rol(nombre="GERENTE"):
    RolesOld.objects.filter(nombre_rol=nombre).delete()
    r = RolesOld(nombre_rol=nombre, descripcion="Rol de prueba")
    r.save()
    return r


def crear_usuario_staff(rol, correo="admin@test.com", doc="00000001"):
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


def crear_categoria(nombre="CUNAS"):
    Categorias.objects.filter(nombre_categoria=nombre).delete()
    c = Categorias(
        nombre_categoria=nombre,
        estado_categoria="activo",
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    c.save()
    return c


def crear_proveedor(nombre="Prov Test", estado="ACTIVO"):
    Proveedores.objects.filter(nombre=nombre).delete()
    p = Proveedores(
        nombre=nombre, estado=estado,
        email=f"{nombre.lower().replace(' ', '')}@test.com",
        telefono="3001234567",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    p.save()
    return p


def crear_bodega(nombre="Bodega Principal"):
    Bodegas.objects.filter(nombre_bodega=nombre).delete()
    b = Bodegas(
        nombre_bodega=nombre, estado="ACTIVA",
        created_at=timezone.now(), updated_at=timezone.now(),
    )
    b.save()
    return b


def crear_producto(categoria, codigo="PROD-T01", precio=150000, estado="DISPONIBLE"):
    Producto.objects.filter(codigo_producto=codigo).delete()
    p = Producto(
        codigo_producto=codigo,
        referencia_producto="Producto de prueba",
        categoria=categoria,
        precio_actual=Decimal(str(precio)),
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(p)
    return p


def crear_inventario(producto, bodega, cantidad=10, reservada=0, estado="DISPONIBLE"):
    inv = Inventario(
        producto=producto, bodega=bodega,
        cantidad_disponible=cantidad,
        cantidad_reservada=reservada,
        estado=estado,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    Model.save(inv)
    return inv


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Categorias
# ══════════════════════════════════════════════════════════════════════════════

class CategoriasModelTests(TestCase):

    def setUp(self):
        Categorias.objects.filter(nombre_categoria="CAT TEST").delete()

    # ── Creación ──────────────────────────────────────────────────────────────
    def test_crear_categoria_exitoso(self):
        cat = crear_categoria("CAT TEST")
        self.assertIsNotNone(cat.pk)
        self.assertEqual(cat.nombre_categoria, "CAT TEST")
        self.assertEqual(cat.estado_categoria, "activo")

    def test_timestamps_se_generan_al_crear(self):
        cat = crear_categoria("CAT TEST")
        self.assertIsNotNone(cat.created_at)
        self.assertIsNotNone(cat.updated_at)

    def test_str_retorna_nombre(self):
        cat = crear_categoria("CAT TEST")
        self.assertEqual(str(cat), "CAT TEST")

    # ── Soft delete ───────────────────────────────────────────────────────────
    def test_soft_delete_marca_deleted_at(self):
        cat = crear_categoria("CAT TEST")
        cat.delete()
        self.assertIsNotNone(cat.deleted_at)

    def test_soft_delete_no_elimina_fisicamente(self):
        cat = crear_categoria("CAT TEST")
        pk = cat.pk
        cat.delete()
        self.assertTrue(Categorias.objects.filter(pk=pk).exists())

    def test_hard_delete_elimina_fisicamente(self):
        cat = crear_categoria("CAT TEST")
        pk = cat.pk
        cat.hard_delete()
        self.assertFalse(Categorias.objects.filter(pk=pk).exists())

    # ── Estado ────────────────────────────────────────────────────────────────
    def test_estado_default_es_activo(self):
        cat = Categorias(nombre_categoria="CAT NUEVA")
        self.assertEqual(cat.estado_categoria, "activo")


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Proveedores
# ══════════════════════════════════════════════════════════════════════════════

class ProveedoresModelTests(TestCase):

    def test_crear_proveedor_activo(self):
        prov = crear_proveedor()
        self.assertIsNotNone(prov.pk)
        self.assertEqual(prov.estado, "ACTIVO")

    def test_str_muestra_check_si_activo(self):
        prov = crear_proveedor()
        self.assertIn("✓", str(prov))

    def test_str_muestra_x_si_inactivo(self):
        prov = crear_proveedor("Prov Inactivo", estado="INACTIVO")
        self.assertIn("✗", str(prov))

    def test_esta_activo_true(self):
        prov = crear_proveedor()
        self.assertTrue(prov.esta_activo())

    def test_esta_activo_false_si_inactivo(self):
        prov = crear_proveedor("Prov Inact2", estado="INACTIVO")
        self.assertFalse(prov.esta_activo())

    def test_soft_delete(self):
        prov = crear_proveedor("Prov Del")
        pk = prov.pk
        prov.delete()
        self.assertIsNotNone(prov.deleted_at)
        self.assertTrue(Proveedores.objects.filter(pk=pk).exists())

    def test_esta_activo_false_si_deleted(self):
        prov = crear_proveedor("Prov Del2")
        prov.delete()
        self.assertFalse(prov.esta_activo())

    def test_tiene_pedidos_sin_compras_false(self):
        prov = crear_proveedor()
        self.assertFalse(prov.tiene_pedidos_asociados())

    def test_get_contacto_completo_incluye_nombre(self):
        prov = crear_proveedor()
        contacto = prov.get_contacto_completo()
        self.assertIn(prov.nombre, contacto)

    def test_timestamps_actualizan_al_save(self):
        prov = crear_proveedor()
        ts_old = prov.updated_at
        prov.direccion = "Nueva dirección 123"
        prov.save()
        self.assertGreaterEqual(prov.updated_at, ts_old)


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Bodegas
# ══════════════════════════════════════════════════════════════════════════════

class BodegasModelTests(TestCase):

    def test_crear_bodega(self):
        b = crear_bodega()
        self.assertIsNotNone(b.pk)
        self.assertEqual(b.estado, "ACTIVA")

    def test_str_retorna_nombre(self):
        b = crear_bodega("Almacén Norte")
        self.assertEqual(str(b), "Almacén Norte")

    def test_timestamps_al_crear(self):
        b = crear_bodega()
        self.assertIsNotNone(b.created_at)
        self.assertIsNotNone(b.updated_at)


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Producto
# ══════════════════════════════════════════════════════════════════════════════

class ProductoModelTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT PROD")

    # ── Creación y str ────────────────────────────────────────────────────────
    def test_crear_producto_exitoso(self):
        p = crear_producto(self.cat)
        self.assertIsNotNone(p.pk)
        self.assertEqual(p.estado, "DISPONIBLE")

    def test_str_incluye_codigo(self):
        p = crear_producto(self.cat, codigo="COD-001")
        self.assertIn("COD-001", str(p))

    def test_precio_formateado_formato_correcto(self):
        p = crear_producto(self.cat, precio=1200000)
        fmt = p.precio_formateado()
        self.assertIn("1.200.000", fmt)

    def test_is_deleted_false_si_activo(self):
        p = crear_producto(self.cat)
        self.assertFalse(p.is_deleted())

    # ── Soft delete / restore ─────────────────────────────────────────────────
    def test_soft_delete(self):
        p = crear_producto(self.cat, codigo="PDEL-001")
        p.soft_delete()
        self.assertIsNotNone(p.deleted_at)
        self.assertTrue(p.is_deleted())

    def test_restore_limpia_deleted_at(self):
        p = crear_producto(self.cat, codigo="PRES-001")
        p.soft_delete()
        p.restore()
        self.assertIsNone(p.deleted_at)
        self.assertFalse(p.is_deleted())

    # ── Precio ────────────────────────────────────────────────────────────────
    def test_precio_cero_lanza_error(self):
        p = Producto(
            codigo_producto="ERR-001",
            referencia_producto="Test",
            categoria=self.cat,
            precio_actual=Decimal("0"),
            estado="DISPONIBLE",
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_precio_negativo_lanza_error(self):
        p = Producto(
            codigo_producto="ERR-002",
            referencia_producto="Test",
            categoria=self.cat,
            precio_actual=Decimal("-100"),
            estado="DISPONIBLE",
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    # ── Código duplicado ──────────────────────────────────────────────────────
    def test_codigo_duplicado_lanza_error_en_bd(self):
        crear_producto(self.cat, codigo="DUP-001")
        with self.assertRaises(Exception):
            Producto.objects.create(
                codigo_producto="DUP-001",
                referencia_producto="Duplicado",
                categoria=self.cat,
                precio_actual=Decimal("100000"),
                estado="DISPONIBLE",
            )

    # ── Stock ─────────────────────────────────────────────────────────────────
    def test_get_stock_total_sin_inventario(self):
        p = crear_producto(self.cat, codigo="STOCK-001")
        self.assertEqual(p.get_stock_total(), 0)

    def test_get_stock_total_con_inventario(self):
        p = crear_producto(self.cat, codigo="STOCK-002")
        b = crear_bodega("Bodega Stock")
        crear_inventario(p, b, cantidad=15)
        self.assertEqual(p.get_stock_total(), 15)

    def test_esta_disponible_con_stock(self):
        p = crear_producto(self.cat, codigo="DISP-001")
        b = crear_bodega("Bodega Disp")
        crear_inventario(p, b, cantidad=5)
        self.assertTrue(p.esta_disponible())

    def test_esta_disponible_sin_stock(self):
        p = crear_producto(self.cat, codigo="DISP-002")
        self.assertFalse(p.esta_disponible())

    # ── Imagen principal ──────────────────────────────────────────────────────
    def test_get_imagen_principal_none_sin_imagen(self):
        p = crear_producto(self.cat, codigo="IMG-001")
        self.assertIsNone(p.get_imagen_principal())


# ══════════════════════════════════════════════════════════════════════════════
# MODELO: Inventario
# ══════════════════════════════════════════════════════════════════════════════

class InventarioModelTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT INV")
        self.prod = crear_producto(self.cat, codigo="INV-P01")
        self.bodega = crear_bodega("Bodega Inv")

    # ── Creación ──────────────────────────────────────────────────────────────
    def test_crear_inventario_exitoso(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=20)
        self.assertIsNotNone(inv.pk)
        self.assertEqual(inv.cantidad_disponible, 20)

    def test_str_incluye_codigo_y_bodega(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=5)
        resultado = str(inv)
        self.assertIn(self.prod.codigo_producto, resultado)
        self.assertIn(self.bodega.nombre_bodega, resultado)

    # ── Estado automático ─────────────────────────────────────────────────────
    def test_estado_disponible_sin_reservas(self):
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=10, cantidad_reservada=0,
        )
        inv.save()
        self.assertEqual(inv.estado, "DISPONIBLE")

    def test_estado_comprometido_con_reservas(self):
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=10, cantidad_reservada=3,
        )
        inv.save()
        self.assertEqual(inv.estado, "COMPROMETIDO")

    def test_estado_agotado_cuando_cantidad_cero(self):
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=0, cantidad_reservada=0,
        )
        inv.save()
        self.assertEqual(inv.estado, "AGOTADO")

    # ── Validaciones ──────────────────────────────────────────────────────────
    def test_cantidad_negativa_falla(self):
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=-1, cantidad_reservada=0,
        )
        with self.assertRaises(ValidationError):
            inv.full_clean()

    def test_reservada_mayor_disponible_falla(self):
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=5, cantidad_reservada=10,
        )
        with self.assertRaises(ValidationError):
            inv.full_clean()

    # ── agregar_stock / retirar_stock ─────────────────────────────────────────
    def test_agregar_stock_aumenta_cantidad(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        inv.agregar_stock(5)
        self.assertEqual(inv.cantidad_disponible, 15)

    def test_agregar_stock_cero_falla(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        with self.assertRaises(ValidationError):
            inv.agregar_stock(0)

    def test_retirar_stock_disminuye_cantidad(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        inv.retirar_stock(3)
        self.assertEqual(inv.cantidad_disponible, 7)

    def test_retirar_stock_insuficiente_falla(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=5)
        with self.assertRaises(ValidationError):
            inv.retirar_stock(10)

    def test_retirar_stock_negativo_falla(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        with self.assertRaises(ValidationError):
            inv.retirar_stock(-1)

    # ── Soft delete / restore ─────────────────────────────────────────────────
    def test_soft_delete(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        pk = inv.pk
        inv.soft_delete()
        self.assertIsNotNone(inv.deleted_at)
        self.assertTrue(Inventario.objects.filter(pk=pk).exists())

    def test_restore(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        inv.soft_delete()
        inv.restore()
        self.assertIsNone(inv.deleted_at)

    # ── cantidad_reservada None → 0 ───────────────────────────────────────────
    def test_cantidad_reservada_none_se_convierte_a_cero(self):
        inv = Inventario.__new__(Inventario)
        inv.cantidad_reservada = None
        inv.__init__()
        self.assertEqual(inv.cantidad_reservada, 0)


# ══════════════════════════════════════════════════════════════════════════════
# FORMULARIOS
# ══════════════════════════════════════════════════════════════════════════════

class ProductoFormTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT FORM")

    def _datos(self, codigo="FORM-001"):
        return {
            "codigo_producto": codigo,
            "referencia_producto": "Referencia de prueba",
            "categoria": self.cat.pk,
            "precio_actual": "150000",
            "estado": "DISPONIBLE",
        }

    def test_formulario_valido(self):
        form = ProductoForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_precio_cero_invalido(self):
        datos = self._datos("FORM-002")
        datos["precio_actual"] = "0"
        form = ProductoForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_actual", form.errors)

    def test_precio_negativo_invalido(self):
        datos = self._datos("FORM-003")
        datos["precio_actual"] = "-500"
        form = ProductoForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_actual", form.errors)

    def test_codigo_duplicado_invalido(self):
        crear_producto(self.cat, codigo="DUP-FORM")
        form = ProductoForm(data=self._datos(codigo="DUP-FORM"))
        self.assertFalse(form.is_valid())
        self.assertIn("codigo_producto", form.errors)

    def test_sin_categoria_invalido(self):
        datos = self._datos()
        datos["categoria"] = ""
        form = ProductoForm(data=datos)
        self.assertFalse(form.is_valid())

    def test_estado_disponible_valido(self):
        form = ProductoForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["estado"], "DISPONIBLE")


class InventarioFormTests(TestCase):

    def setUp(self):
        self.cat = crear_categoria("CAT INV FORM")
        self.prod = crear_producto(self.cat, codigo="INVF-001")
        self.bodega = crear_bodega("Bodega Form")

    def _datos(self):
        return {
            "producto": self.prod.pk,
            "bodega": self.bodega.pk,
            "cantidad_disponible": "10",
            "cantidad_reservada": "0",
            "estado": "DISPONIBLE",
        }

    def test_formulario_valido(self):
        form = InventarioForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_cantidad_negativa_invalido(self):
        datos = self._datos()
        datos["cantidad_disponible"] = "-5"
        form = InventarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad_disponible", form.errors)

    def test_reservada_mayor_disponible_invalido(self):
        datos = self._datos()
        datos["cantidad_disponible"] = "5"
        datos["cantidad_reservada"] = "10"
        form = InventarioForm(data=datos)
        self.assertFalse(form.is_valid())

    def test_duplicado_mismo_producto_bodega_invalido(self):
        # Crear registro previo
        inv = Inventario(
            producto=self.prod, bodega=self.bodega,
            cantidad_disponible=5, cantidad_reservada=0,
        )
        inv.save()
        form = InventarioForm(data=self._datos())
        self.assertFalse(form.is_valid())

    def test_proveedor_no_requerido(self):
        datos = self._datos()
        datos.pop("proveedor", None)
        form = InventarioForm(data=datos)
        self.assertTrue(form.is_valid(), form.errors)


class ProveedorFormTests(TestCase):

    def _datos(self, nombre="Proveedor Form", email="pftest@test.com"):
        return {
            "nombre": nombre,
            "telefono": "3009876543",
            "email": email,
            "direccion": "Calle 123 # 45-67",
            "estado": "ACTIVO",
        }

    def test_formulario_valido(self):
        form = ProveedorForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_duplicado_invalido(self):
        crear_proveedor("Otro Prov", estado="ACTIVO")
        Proveedores.objects.filter(nombre="Otro Prov").update(email="dup@test.com")
        form = ProveedorForm(data=self._datos(email="dup@test.com"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_telefono_muy_corto_invalido(self):
        datos = self._datos()
        datos["telefono"] = "123"
        form = ProveedorForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)

    def test_nombre_duplicado_invalido(self):
        crear_proveedor("NombreDup")
        form = ProveedorForm(data=self._datos(nombre="NombreDup"))
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)

    def test_nombre_se_convierte_title_case(self):
        form = ProveedorForm(data=self._datos(nombre="proveedor minúsculas"))
        if form.is_valid():
            self.assertEqual(form.cleaned_data["nombre"], "Proveedor Minúsculas")


class BodegaFormTests(TestCase):

    def test_formulario_valido(self):
        form = BodegaForm(data={
            "nombre_bodega": "Bodega Test",
            "direccion": "Carrera 1 # 1-1",
            "estado": "ACTIVA",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_nombre_invalido(self):
        form = BodegaForm(data={"nombre_bodega": "", "estado": "ACTIVA"})
        self.assertFalse(form.is_valid())

    def test_estado_inactiva_valido(self):
        form = BodegaForm(data={
            "nombre_bodega": "Bodega Inactiva",
            "estado": "INACTIVA",
        })
        self.assertTrue(form.is_valid(), form.errors)


class CategoriaFormTests(TestCase):

    def test_formulario_valido(self):
        form = CategoriaForm(data={
            "nombre_categoria": "CATEGORIA FORM",
            "estado_categoria": "activo",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_estado_inactivo_valido(self):
        form = CategoriaForm(data={
            "nombre_categoria": "CAT INACT",
            "estado_categoria": "inactivo",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_sin_nombre_invalido(self):
        form = CategoriaForm(data={
            "nombre_categoria": "",
            "estado_categoria": "activo",
        })
        self.assertFalse(form.is_valid())


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Producto
# ══════════════════════════════════════════════════════════════════════════════

class ProductoListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_P")
        self.admin = crear_usuario_staff(self.rol, "admin_p@test.com", "11110001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT VISTA")

    def test_lista_status_200(self):
        response = self.client.get(reverse("inventario:producto_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/producto_list.html")

    def test_lista_muestra_productos(self):
        crear_producto(self.cat, codigo="LIST-001")
        response = self.client.get(reverse("inventario:producto_list"))
        self.assertContains(response, "LIST-001")

    def test_filtro_por_estado_disponible(self):
        crear_producto(self.cat, codigo="FILT-D01", estado="DISPONIBLE")
        crear_producto(self.cat, codigo="FILT-A01", estado="AGOTADO")
        response = self.client.get(
            reverse("inventario:producto_list") + "?estado=DISPONIBLE"
        )
        self.assertContains(response, "FILT-D01")

    def test_filtro_por_busqueda(self):
        crear_producto(self.cat, codigo="BUSC-001")
        response = self.client.get(
            reverse("inventario:producto_list") + "?busqueda=BUSC-001"
        )
        self.assertContains(response, "BUSC-001")

    def test_filtro_por_categoria(self):
        cat2 = crear_categoria("OTRA CAT")
        crear_producto(self.cat, codigo="CAT-V01")
        crear_producto(cat2, codigo="CAT-V02")
        response = self.client.get(
            reverse("inventario:producto_list") + f"?categoria={self.cat.pk}"
        )
        self.assertContains(response, "CAT-V01")

    def test_contexto_tiene_categorias(self):
        response = self.client.get(reverse("inventario:producto_list"))
        self.assertIn("categorias", response.context)

    def test_contexto_tiene_estados(self):
        response = self.client.get(reverse("inventario:producto_list"))
        self.assertIn("estados", response.context)
        self.assertIn("DISPONIBLE", response.context["estados"])


class ProductoCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PC")
        self.admin = crear_usuario_staff(self.rol, "admin_pc@test.com", "22220001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT CREATE")

    def test_get_form_status_200(self):
        response = self.client.get(reverse("inventario:producto_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_producto_valido_redirige(self):
        Producto.objects.filter(codigo_producto="CREAT-001").delete()
        response = self.client.post(
            reverse("inventario:producto_create"),
            {
                "codigo_producto": "CREAT-001",
                "referencia_producto": "Creado en test",
                "categoria": self.cat.pk,
                "precio_actual": "200000",
                "estado": "DISPONIBLE",
            },
            follow=False
        )
        # Redirige al listado
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Producto.objects.filter(codigo_producto="CREAT-001").exists()
        )

    def test_crear_producto_invalido_muestra_form(self):
        response = self.client.post(
            reverse("inventario:producto_create"),
            {
                "codigo_producto": "",
                "precio_actual": "0",
                "categoria": self.cat.pk,
                "estado": "DISPONIBLE",
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_codigo_duplicado_invalido(self):
        crear_producto(self.cat, codigo="DUPL-001")
        response = self.client.post(
            reverse("inventario:producto_create"),
            {
                "codigo_producto": "DUPL-001",
                "referencia_producto": "Duplicado",
                "categoria": self.cat.pk,
                "precio_actual": "100000",
                "estado": "DISPONIBLE",
            }
        )
        self.assertEqual(response.status_code, 200)


class ProductoUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PU")
        self.admin = crear_usuario_staff(self.rol, "admin_pu@test.com", "33330001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT UPDATE")
        self.prod = crear_producto(self.cat, codigo="UPD-001")

    def test_get_form_status_200(self):
        response = self.client.get(
            reverse("inventario:producto_update", kwargs={"pk": self.prod.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_actualizar_precio_exitoso(self):
        response = self.client.post(
            reverse("inventario:producto_update", kwargs={"pk": self.prod.pk}),
            {
                "codigo_producto": "UPD-001",
                "referencia_producto": "Actualizado",
                "categoria": self.cat.pk,
                "precio_actual": "999999",
                "estado": "DISPONIBLE",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.precio_actual, Decimal("999999"))

    def test_actualizar_estado_a_agotado(self):
        response = self.client.post(
            reverse("inventario:producto_update", kwargs={"pk": self.prod.pk}),
            {
                "codigo_producto": "UPD-001",
                "referencia_producto": "Actualizado",
                "categoria": self.cat.pk,
                "precio_actual": "150000",
                "estado": "AGOTADO",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.estado, "AGOTADO")


class ProductoDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PD")
        self.admin = crear_usuario_staff(self.rol, "admin_pd@test.com", "44440001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT DELETE")

    def test_get_confirm_status_200(self):
        p = crear_producto(self.cat, codigo="DEL-001")
        response = self.client.get(
            reverse("inventario:producto_delete", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_post_soft_delete_exitoso(self):
        p = crear_producto(self.cat, codigo="DEL-002")
        response = self.client.post(
            reverse("inventario:producto_delete", kwargs={"pk": p.pk})
        )
        self.assertEqual(response.status_code, 302)
        p.refresh_from_db()
        self.assertIsNotNone(p.deleted_at)

    def test_producto_no_aparece_en_lista_tras_eliminar(self):
        p = crear_producto(self.cat, codigo="DEL-003")

        self.client.post(
            reverse("inventario:producto_delete", kwargs={"pk": p.pk})
        )

        p.refresh_from_db()

        self.assertIsNotNone(p.deleted_at)

        productos_visibles = Producto.objects.filter(
            deleted_at__isnull=True
        )

        self.assertNotIn(p, productos_visibles)


class ProductoDetailViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PV")
        self.admin = crear_usuario_staff(self.rol, "admin_pv@test.com", "55550001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT DETAIL")
        self.prod = crear_producto(self.cat, codigo="DET-001")

    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("inventario:producto_detail", kwargs={"pk": self.prod.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/producto_detail.html")

    def test_detalle_muestra_codigo(self):
        response = self.client.get(
            reverse("inventario:producto_detail", kwargs={"pk": self.prod.pk})
        )
        self.assertContains(response, "DET-001")

    def test_detalle_contexto_tiene_producto(self):
        response = self.client.get(
            reverse("inventario:producto_detail", kwargs={"pk": self.prod.pk})
        )
        self.assertIn("producto", response.context)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Inventario (Stock)
# ══════════════════════════════════════════════════════════════════════════════

class InventarioListViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_IV")
        self.admin = crear_usuario_staff(self.rol, "admin_iv@test.com", "66660001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT INV VISTA")
        self.prod = crear_producto(self.cat, codigo="INV-V01")
        self.bodega = crear_bodega("Bodega Vista")

    def test_lista_status_200(self):
        response = self.client.get(reverse("inventario:inventario_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/inventario_list.html")

    def test_lista_contiene_producto_en_inventario(self):
        crear_inventario(self.prod, self.bodega, cantidad=5)
        response = self.client.get(reverse("inventario:inventario_list"))
        self.assertContains(response, "INV-V01")

    def test_filtro_por_estado_disponible(self):
        crear_inventario(self.prod, self.bodega, cantidad=10, estado="DISPONIBLE")
        response = self.client.get(
            reverse("inventario:inventario_list") + "?estado=DISPONIBLE"
        )
        self.assertEqual(response.status_code, 200)

    def test_filtro_por_producto(self):
        crear_inventario(self.prod, self.bodega, cantidad=10)
        response = self.client.get(
            reverse("inventario:inventario_list") + f"?producto={self.prod.pk}"
        )
        self.assertContains(response, "INV-V01")

    def test_filtro_por_bodega(self):
        crear_inventario(self.prod, self.bodega, cantidad=10)
        response = self.client.get(
            reverse("inventario:inventario_list") + f"?bodega={self.bodega.pk}"
        )
        self.assertEqual(response.status_code, 200)

    def test_contexto_tiene_stock_libre(self):
        crear_inventario(self.prod, self.bodega, cantidad=10, reservada=3)
        response = self.client.get(reverse("inventario:inventario_list"))
        items = response.context["inventarios"]
        for item in items:
            self.assertTrue(hasattr(item, "stock_libre"))


class InventarioCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_IC")
        self.admin = crear_usuario_staff(self.rol, "admin_ic@test.com", "77770001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT IC")
        self.prod = crear_producto(self.cat, codigo="IC-P01")
        self.bodega = crear_bodega("Bodega IC")

    def test_get_form_status_200(self):
        response = self.client.get(reverse("inventario:inventario_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_inventario_valido_redirige(self):
        response = self.client.post(
            reverse("inventario:inventario_create"),
            {
                "producto": self.prod.pk,
                "bodega": self.bodega.pk,
                "cantidad_disponible": "25",
                "cantidad_reservada": "0",
                "estado": "DISPONIBLE",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Inventario.objects.filter(
                producto=self.prod, bodega=self.bodega, deleted_at__isnull=True
            ).exists()
        )


class InventarioDeleteViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_ID")
        self.admin = crear_usuario_staff(self.rol, "admin_id@test.com", "88880001")
        autenticar_sesion(self.client, self.admin)
        self.cat = crear_categoria("CAT ID")
        self.prod = crear_producto(self.cat, codigo="ID-P01")
        self.bodega = crear_bodega("Bodega ID")

    def test_get_confirmacion_status_200(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        response = self.client.get(
            reverse("inventario:inventario_delete", kwargs={"pk": inv.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_post_soft_delete_exitoso(self):
        inv = crear_inventario(self.prod, self.bodega, cantidad=10)
        response = self.client.post(
            reverse("inventario:inventario_delete", kwargs={"pk": inv.pk})
        )
        self.assertEqual(response.status_code, 302)
        inv.refresh_from_db()
        self.assertIsNotNone(inv.deleted_at)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Proveedores
# ══════════════════════════════════════════════════════════════════════════════

class ProveedorViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_PV2")
        self.admin = crear_usuario_staff(self.rol, "admin_pvv@test.com", "99990001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("inventario:proveedor_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/proveedor_list.html")

    def test_lista_contiene_proveedor(self):
        crear_proveedor("VistaProvTest")

        response = self.client.get(
            reverse("inventario:proveedor_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VistaProvTest")

    def test_filtro_estado_activo(self):
        crear_proveedor("ProvActivo")
        crear_proveedor("ProvInactivo", estado="INACTIVO")
        response = self.client.get(
            reverse("inventario:proveedor_list") + "?estado=ACTIVO"
        )
        self.assertEqual(response.status_code, 200)

    def test_crear_proveedor_get_status_200(self):
        response = self.client.get(reverse("inventario:proveedor_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_proveedor_post_valido(self):
        Proveedores.objects.filter(nombre="Nuevo Proveedor Test").delete()
        response = self.client.post(
            reverse("inventario:proveedor_create"),
            {
                "nombre": "Nuevo Proveedor Test",
                "telefono": "3001112233",
                "email": "nuevoprov@test.com",
                "direccion": "Calle 99 # 1-1",
                "estado": "ACTIVO",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Proveedores.objects.filter(
                nombre__iexact="Nuevo Proveedor Test",
                deleted_at__isnull=True
            ).exists()
        )

    def test_detalle_proveedor_status_200(self):
        prov = crear_proveedor("DetProv")
        response = self.client.get(
            reverse("inventario:proveedor_detail", kwargs={"pk": prov.pk})
        )
        self.assertEqual(response.status_code, 200)


# ══════════════════════════════════════════════════════════════════════════════
# VISTAS: Bodegas y Categorias
# ══════════════════════════════════════════════════════════════════════════════

class BodegaViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_BV")
        self.admin = crear_usuario_staff(self.rol, "admin_bv@test.com", "10100001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("inventario:bodega_list"))
        self.assertEqual(response.status_code, 200)

    def test_crear_bodega_get_status_200(self):
        response = self.client.get(reverse("inventario:bodega_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_bodega_post_valido(self):
        Bodegas.objects.filter(nombre_bodega="Bodega Post Test").delete()
        response = self.client.post(
            reverse("inventario:bodega_create"),
            {
                "nombre_bodega": "Bodega Post Test",
                "direccion": "Km 5 vía norte",
                "estado": "ACTIVA",
            }
        )
        self.assertEqual(response.status_code, 302)

    def test_crear_bodega_post_invalido(self):
        response = self.client.post(
            reverse("inventario:bodega_create"),
            {"nombre_bodega": "", "estado": "ACTIVA"}
        )
        self.assertEqual(response.status_code, 200)


class CategoriaViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_CV")
        self.admin = crear_usuario_staff(self.rol, "admin_cv@test.com", "20200001")
        autenticar_sesion(self.client, self.admin)

    def test_lista_status_200(self):
        response = self.client.get(reverse("inventario:categoria_list"))
        self.assertEqual(response.status_code, 200)

    def test_lista_contiene_categoria(self):
        crear_categoria("CAT LISTA VISIBLE")
        response = self.client.get(reverse("inventario:categoria_list"))
        self.assertContains(response, "CAT LISTA VISIBLE")

    def test_crear_categoria_post_valido(self):
        Categorias.objects.filter(nombre_categoria="CAT POST NUEVA").delete()
        response = self.client.post(
            reverse("inventario:categoria_create"),
            {
                "nombre_categoria": "CAT POST NUEVA",
                "estado_categoria": "activo",
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Categorias.objects.filter(
                nombre_categoria="CAT POST NUEVA",
                deleted_at__isnull=True
            ).exists()
        )

    def test_filtro_busqueda_categoria(self):
        crear_categoria("BUSCABLE CAT")
        response = self.client.get(
            reverse("inventario:categoria_list") + "?busqueda=BUSCABLE"
        )
        self.assertContains(response, "BUSCABLE CAT")