from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password

from usuarios.models import RolesOld, Usuarios
from usuarios.forms import UsuarioForm, UsuarioUpdateForm, RolForm
import pytest

from .utils import crear_rol, crear_usuario, autenticar_sesion


# ═════════════════════════════════════════════════════════════════════════════
# MODELO: RolesOld
# ═════════════════════════════════════════════════════════════════════════════

class RolesOldModelTests(TestCase):

    def setUp(self):
        RolesOld.objects.filter(nombre_rol="TESTER").delete()

    # ── Creación ──────────────────────────────────────────────────────────────
    def test_crear_rol_exitoso(self):
        rol = crear_rol("TESTER", "Descripción de prueba")
        self.assertIsNotNone(rol.pk)
        self.assertIsNotNone(rol.created_at)
        self.assertIsNotNone(rol.updated_at)

    def test_str_retorna_nombre(self):
        rol = crear_rol("TESTER")
        self.assertEqual(str(rol), "TESTER")

    # ── Validaciones ──────────────────────────────────────────────────────────
    def test_nombre_muy_corto_falla(self):
        rol = RolesOld(nombre_rol="AB", descripcion="x")
        with self.assertRaises(ValidationError):
            rol.full_clean()

    def test_nombre_duplicado_falla(self):
        crear_rol("TESTER")
        with self.assertRaises(Exception):
            RolesOld.objects.create(nombre_rol="TESTER")

    # ── Soft delete ───────────────────────────────────────────────────────────
    def test_soft_delete_sin_usuarios(self):
        rol = crear_rol("TESTER")
        rol.delete()
        self.assertIsNotNone(rol.deleted_at)
        self.assertTrue(RolesOld.objects.filter(pk=rol.pk).exists())

    def test_soft_delete_con_usuarios_falla(self):
        rol = crear_rol("TESTER")
        crear_usuario(rol, correo="x@x.com", documento="99999901")
        with self.assertRaises(ValidationError):
            rol.delete()

    # ── Métodos de negocio ────────────────────────────────────────────────────
    def test_get_total_usuarios(self):
        rol = crear_rol("TESTER")
        crear_usuario(rol, correo="a@a.com", documento="11111101")
        crear_usuario(rol, correo="b@b.com", documento="22222201")
        self.assertEqual(rol.get_total_usuarios(), 2)

    def test_puede_eliminarse_false_con_usuarios(self):
        rol = crear_rol("TESTER")
        crear_usuario(rol, correo="c@c.com", documento="33333301")
        self.assertFalse(rol.puede_eliminarse())

    def test_puede_eliminarse_true_sin_usuarios(self):
        rol = crear_rol("TESTER")
        self.assertTrue(rol.puede_eliminarse())


# ═════════════════════════════════════════════════════════════════════════════
# MODELO: Usuarios
# ═════════════════════════════════════════════════════════════════════════════

class UsuariosModelTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("GERENTE_M")

    # ── Propiedades Django Auth ───────────────────────────────────────────────
    def test_is_authenticated_activo(self):
        u = crear_usuario(self.rol, correo="auth@test.com", documento="44444401")
        self.assertTrue(u.is_authenticated)

    def test_is_authenticated_inactivo(self):
        u = crear_usuario(self.rol, correo="inact@test.com", documento="55555501",
                        estado="INACTIVO")
        self.assertFalse(u.is_authenticated)

    def test_is_staff_true(self):
        u = crear_usuario(self.rol, correo="staff@test.com", documento="66666601")
        self.assertTrue(u.is_staff)

    def test_username_es_correo(self):
        u = crear_usuario(self.rol, correo="user@test.com", documento="77777701")
        self.assertEqual(u.username, "user@test.com")

    def test_get_full_name(self):
        u = crear_usuario(self.rol, nombres="Juan", apellidos="Pérez",
                        correo="jp@test.com", documento="88888801")
        self.assertEqual(u.get_full_name(), "Juan Pérez")

    def test_str_contiene_nombre(self):
        u = crear_usuario(self.rol, nombres="Ana", apellidos="López",
                        correo="al@test.com", documento="99999901")
        self.assertIn("Ana", str(u))

    # ── Contraseña ────────────────────────────────────────────────────────────
    def test_check_password_correcto(self):
        u = crear_usuario(self.rol, correo="cp@test.com", documento="10101001",
                        contrasena="MiClave123")
        self.assertTrue(u.check_password("MiClave123"))

    def test_check_password_incorrecto(self):
        u = crear_usuario(self.rol, correo="cp2@test.com", documento="20202001",
                        contrasena="MiClave123")
        self.assertFalse(u.check_password("ClaveWrong"))

    # ── Soft delete / restore ─────────────────────────────────────────────────
    def test_soft_delete(self):
        u = crear_usuario(self.rol, correo="del@test.com", documento="30303001")
        u.delete()
        self.assertIsNotNone(u.deleted_at)
        self.assertEqual(u.estado, "INACTIVO")
        self.assertTrue(Usuarios.objects.filter(pk=u.pk).exists())

    def test_restore(self):
        u = crear_usuario(self.rol, correo="res@test.com", documento="40404001")
        u.delete()
        u.restore()
        self.assertIsNone(u.deleted_at)
        self.assertEqual(u.estado, "ACTIVO")

    # ── Cambios de estado ─────────────────────────────────────────────────────
    def test_activar(self):
        u = crear_usuario(self.rol, correo="act@test.com", documento="50505001",
                            estado="INACTIVO")
        u.activar()
        self.assertEqual(u.estado, "ACTIVO")

    def test_desactivar(self):
        u = crear_usuario(self.rol, correo="des@test.com", documento="60606001")
        u.desactivar()
        self.assertEqual(u.estado, "INACTIVO")

    def test_suspender(self):
        u = crear_usuario(self.rol, correo="sus@test.com", documento="70707001")
        u.suspender()
        self.assertEqual(u.estado, "SUSPENDIDO")

    # ── has_role / has_any_role ───────────────────────────────────────────────
    def test_has_role_correcto(self):
        u = crear_usuario(self.rol, correo="hr@test.com", documento="80808001")
        self.assertTrue(u.has_role("GERENTE_M"))

    def test_has_role_incorrecto(self):
        u = crear_usuario(self.rol, correo="hr2@test.com", documento="90909001")
        self.assertFalse(u.has_role("OTRO"))

    def test_has_any_role_verdadero(self):
        u = crear_usuario(self.rol, correo="har@test.com", documento="10101002")
        self.assertTrue(u.has_any_role(["GERENTE_M", "OTRO"]))

    def test_has_any_role_falso(self):
        u = crear_usuario(self.rol, correo="har2@test.com", documento="20202002")
        self.assertFalse(u.has_any_role(["NINGUNO"]))

    def test_puede_eliminarse_no_es_ultimo_gerente(self):
        u = crear_usuario(self.rol, correo="pe@test.com", documento="30303002")
        # Con más de un gerente puede eliminarse
        crear_usuario(self.rol, correo="pe2@test.com", documento="40404002")
        self.assertTrue(u.puede_eliminarse())


# ═════════════════════════════════════════════════════════════════════════════
# FORMULARIO: RolForm
# ═════════════════════════════════════════════════════════════════════════════

class RolFormTests(TestCase):

    def setUp(self):
        RolesOld.objects.filter(nombre_rol__in=["NUEVO ROL", "DUPLICADO"]).delete()

    def test_formulario_valido(self):
        form = RolForm(data={
            "nombre_rol": "NUEVO ROL",
            "descripcion": "Descripción suficientemente larga",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_corto_invalido(self):
        form = RolForm(data={"nombre_rol": "AB", "descripcion": "ok"})
        self.assertFalse(form.is_valid())
        self.assertIn("nombre_rol", form.errors)

    def test_descripcion_corta_invalida(self):
        form = RolForm(data={"nombre_rol": "ROL OK", "descripcion": "corta"})
        self.assertFalse(form.is_valid())
        self.assertIn("descripcion", form.errors)

    def test_nombre_duplicado_invalido(self):
        crear_rol("DUPLICADO")
        form = RolForm(data={
            "nombre_rol": "DUPLICADO",
            "descripcion": "Descripción suficientemente larga",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("nombre_rol", form.errors)

    def test_nombre_se_convierte_a_mayusculas(self):
        form = RolForm(data={
            "nombre_rol": "nuevo rol",
            "descripcion": "Descripción suficientemente larga",
        })
        if form.is_valid():
            self.assertEqual(form.cleaned_data["nombre_rol"], "NUEVO ROL")


# ═════════════════════════════════════════════════════════════════════════════
# FORMULARIO: UsuarioForm
# ═════════════════════════════════════════════════════════════════════════════

class UsuarioFormTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("ROL_FORM")
        Usuarios.objects.filter(correo_usuario="form@test.com").delete()
        Usuarios.objects.filter(documento="55667701").delete()

    def _datos(self, correo="form@test.com", doc="55667701"):
        return {
            "nombres": "Nombre",
            "apellidos": "Apellido",
            "documento": doc,
            "correo_usuario": correo,
            "contrasena_usuario": "Segura123",
            "confirmar_contrasena": "Segura123",
            "id_rol": self.rol.pk,
            "estado": "ACTIVO",
        }

    def test_formulario_valido(self):
        form = UsuarioForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

    def test_contrasenas_no_coinciden(self):
        datos = self._datos()
        datos["confirmar_contrasena"] = "OtraClave1"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("confirmar_contrasena", form.errors)

    def test_contrasena_sin_mayuscula(self):
        datos = self._datos()
        datos["contrasena_usuario"] = "sinmayuscula1"
        datos["confirmar_contrasena"] = "sinmayuscula1"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("contrasena_usuario", form.errors)

    def test_contrasena_sin_numero(self):
        datos = self._datos()
        datos["contrasena_usuario"] = "SinNumero"
        datos["confirmar_contrasena"] = "SinNumero"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("contrasena_usuario", form.errors)

    def test_contrasena_muy_corta(self):
        datos = self._datos()
        datos["contrasena_usuario"] = "Ab1"
        datos["confirmar_contrasena"] = "Ab1"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("contrasena_usuario", form.errors)

    def test_correo_invalido(self):
        datos = self._datos()
        datos["correo_usuario"] = "no-es-un-email"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("correo_usuario", form.errors)

    def test_correo_duplicado(self):
        crear_usuario(self.rol, correo="form@test.com", documento="11111102")
        form = UsuarioForm(data=self._datos(correo="form@test.com", doc="22222202"))
        self.assertFalse(form.is_valid())
        self.assertIn("correo_usuario", form.errors)

    def test_documento_duplicado(self):
        crear_usuario(self.rol, correo="otro@test.com", documento="55667701")
        form = UsuarioForm(data=self._datos(correo="nuevo@test.com", doc="55667701"))
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)

    def test_documento_con_letras_invalido(self):
        datos = self._datos()
        datos["documento"] = "ABC123"
        form = UsuarioForm(data=datos)
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)

    def test_save_hashea_contrasena(self):
        form = UsuarioForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()
        self.assertTrue(usuario.contrasena_usuario.startswith("pbkdf2_"))


# ═════════════════════════════════════════════════════════════════════════════
# FORMULARIO: UsuarioUpdateForm
# ═════════════════════════════════════════════════════════════════════════════

class UsuarioUpdateFormTests(TestCase):

    def setUp(self):
        self.rol = crear_rol("ROL_UPD")

    def test_update_valido_sin_contrasena(self):
        form = UsuarioUpdateForm(data={
            "nombres": "Actualizado",
            "apellidos": "Test",
            "documento": "11112201",
            "correo_usuario": "upd@test.com",
            "id_rol": self.rol.pk,
            "estado": "ACTIVO",
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_correo_invalido_falla(self):
        form = UsuarioUpdateForm(data={
            "nombres": "Ok",
            "apellidos": "Ok",
            "documento": "33334401",
            "correo_usuario": "malformado",
            "id_rol": self.rol.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("correo_usuario", form.errors)

    def test_documento_muy_corto_falla(self):
        form = UsuarioUpdateForm(data={
            "nombres": "Ok",
            "apellidos": "Ok",
            "documento": "123",
            "correo_usuario": "ok@test.com",
            "id_rol": self.rol.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("documento", form.errors)


# ═════════════════════════════════════════════════════════════════════════════
# VISTAS: Login / Logout
# ═════════════════════════════════════════════════════════════════════════════

class LoginLogoutViewTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_login_redirige_a_pagina(self):
        response = self.client.get(reverse("usuarios:login"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/pagina/login", response["Location"])

    def test_logout_limpia_sesion(self):
        session = self.client.session
        session["usuario_id"] = 99
        session.save()
        self.client.get(reverse("usuarios:logout"))
        self.assertNotIn("usuario_id", self.client.session)

    def test_logout_redirige(self):
        response = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(response.status_code, 302)


# ═════════════════════════════════════════════════════════════════════════════
# VISTAS: Roles (CRUD)
# ═════════════════════════════════════════════════════════════════════════════

class RolViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_V")
        self.admin = crear_usuario(self.rol, correo="admin_rv@test.com",
                                    documento="61616101")
        autenticar_sesion(self.client, self.admin)

    # ── Lista ─────────────────────────────────────────────────────────────────
    def test_lista_status_200(self):
        response = self.client.get(reverse("usuarios:rol_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/rol_list.html")

    def test_lista_contiene_rol(self):
        response = self.client.get(reverse("usuarios:rol_list"))
        self.assertContains(response, "GERENTE_V")

    def test_lista_busqueda(self):
        response = self.client.get(reverse("usuarios:rol_list") + "?busqueda=GERENTE_V")
        self.assertContains(response, "GERENTE_V")

    # ── Detalle ───────────────────────────────────────────────────────────────
    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("usuarios:rol_detail", kwargs={"pk": self.rol.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/rol_detail.html")

    # ── Crear ─────────────────────────────────────────────────────────────────
    def test_crear_get_status_200(self):
        response = self.client.get(reverse("usuarios:rol_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/rol_form.html")

    def test_crear_post_valido_redirige(self):
        RolesOld.objects.filter(nombre_rol="ROL NUEVO").delete()
        response = self.client.post(reverse("usuarios:rol_create"), {
            "nombre_rol": "ROL NUEVO",
            "descripcion": "Descripción suficientemente larga para pasar",
        })
        self.assertEqual(response.status_code, 302)

    def test_crear_post_invalido_muestra_errores(self):
        response = self.client.post(reverse("usuarios:rol_create"), {
            "nombre_rol": "AB",
            "descripcion": "ok",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "nombre_rol",
                            "El nombre del rol debe tener al menos 3 caracteres")

    # ── Editar ────────────────────────────────────────────────────────────────
    def test_editar_get_status_200(self):
        response = self.client.get(
            reverse("usuarios:rol_update", kwargs={"pk": self.rol.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_editar_post_valido_redirige(self):
        response = self.client.post(
            reverse("usuarios:rol_update", kwargs={"pk": self.rol.pk}),
            {
                "nombre_rol": "GERENTE_V",
                "descripcion": "Descripción actualizada suficientemente larga",
            },
        )
        self.assertEqual(response.status_code, 302)

    # ── Eliminar ──────────────────────────────────────────────────────────────
    def test_eliminar_post_redirige(self):
        rol_del = crear_rol("ROL_A_ELIMINAR")
        response = self.client.post(
            reverse("usuarios:rol_delete", kwargs={"pk": rol_del.pk})
        )
        self.assertEqual(response.status_code, 302)


# ═════════════════════════════════════════════════════════════════════════════
# VISTAS: Usuarios (CRUD)
# ═════════════════════════════════════════════════════════════════════════════

class UsuarioViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("GERENTE_UV")
        self.admin = crear_usuario(self.rol, correo="admin_uv@test.com",
                                    documento="71717101")
        self.target = crear_usuario(self.rol, correo="target_uv@test.com",
                                    documento="72727201")
        autenticar_sesion(self.client, self.admin)

    # ── Lista ─────────────────────────────────────────────────────────────────
    def test_lista_status_200(self):
        response = self.client.get(reverse("usuarios:usuario_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/usuario_list.html")

    def test_lista_contiene_usuario(self):
        response = self.client.get(reverse("usuarios:usuario_list"))
        self.assertContains(response, "target_uv@test.com")

    # ── Detalle ───────────────────────────────────────────────────────────────
    def test_detalle_status_200(self):
        response = self.client.get(
            reverse("usuarios:usuario_detail", kwargs={"pk": self.target.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/usuario_detail.html")

    # ── Crear ─────────────────────────────────────────────────────────────────
    def test_crear_get_status_200(self):
        response = self.client.get(reverse("usuarios:usuario_create"))
        self.assertEqual(response.status_code, 200)

    def test_crear_post_valido(self):
        Usuarios.objects.filter(correo_usuario="nuevo_uv@test.com").delete()
        Usuarios.objects.filter(documento="73737301").delete()
        response = self.client.post(reverse("usuarios:usuario_create"), {
            "nombres": "Nuevo",
            "apellidos": "Usuario",
            "documento": "73737301",
            "correo_usuario": "nuevo_uv@test.com",
            "contrasena_usuario": "Clave1234",
            "confirmar_contrasena": "Clave1234",
            "id_rol": self.rol.pk,
            "estado": "ACTIVO",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Usuarios.objects.filter(correo_usuario="nuevo_uv@test.com").exists()
        )

    def test_crear_post_invalido_muestra_form(self):
        response = self.client.post(reverse("usuarios:usuario_create"), {
            "nombres": "",
            "documento": "1",
            "correo_usuario": "no-email",
            "contrasena_usuario": "abc",
            "confirmar_contrasena": "abc",
            "id_rol": self.rol.pk,
        })
        self.assertEqual(response.status_code, 200)

    # ── Editar ────────────────────────────────────────────────────────────────
    def test_editar_get_status_200(self):
        response = self.client.get(
            reverse("usuarios:usuario_update", kwargs={"pk": self.target.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_editar_post_valido(self):
        response = self.client.post(
            reverse("usuarios:usuario_update", kwargs={"pk": self.target.pk}),
            {
                "nombres": "Editado",
                "apellidos": "Test",
                "documento": "72727201",
                "correo_usuario": "target_uv@test.com",
                "id_rol": self.rol.pk,
                "estado": "ACTIVO",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertEqual(self.target.nombres, "Editado")

    # ── Eliminar ──────────────────────────────────────────────────────────────
    def test_eliminar_post_redirige(self):
        u_del = crear_usuario(self.rol, correo="del_uv@test.com",
                            documento="74747401")
        response = self.client.post(
            reverse("usuarios:usuario_delete", kwargs={"pk": u_del.pk})
        )
        self.assertEqual(response.status_code, 302)


# ═════════════════════════════════════════════════════════════════════════════
# VISTAS: Filtros de la lista de usuarios
# ═════════════════════════════════════════════════════════════════════════════

class UsuarioFiltrosViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.rol = crear_rol("ROL_FIL")
        self.admin = crear_usuario(self.rol, correo="admin_fil@test.com",
                                    documento="81818101")
        self.u_activo = crear_usuario(self.rol, correo="activo_fil@test.com",
                                    documento="82828201")
        self.u_inact = crear_usuario(self.rol, correo="inact_fil@test.com",
                                    documento="83838301", estado="INACTIVO")
        autenticar_sesion(self.client, self.admin)

    def test_filtro_estado_activo(self):
        response = self.client.get(
            reverse("usuarios:usuario_list") + "?estado=ACTIVO"
        )
        self.assertContains(response, "activo_fil@test.com")

    def test_filtro_estado_inactivo(self):
        response = self.client.get(
            reverse("usuarios:usuario_list") + "?estado=INACTIVO"
        )
        self.assertContains(response, "inact_fil@test.com")

    def test_filtro_por_rol(self):
        response = self.client.get(
            reverse("usuarios:usuario_list") + f"?rol={self.rol.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "activo_fil@test.com")

    def test_busqueda_por_correo(self):
        response = self.client.get(
            reverse("usuarios:usuario_list") + "?busqueda=activo_fil"
        )
        self.assertContains(response, "activo_fil@test.com")

    def test_busqueda_sin_resultados(self):
        response = self.client.get(
            reverse("usuarios:usuario_list") + "?busqueda=zzz_no_existe"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "activo_fil@test.com")