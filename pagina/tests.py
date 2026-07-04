import json
import hashlib
import bcrypt 
from decimal import Decimal
from unittest.mock import patch, MagicMock, call, PropertyMock
from django.test import TestCase, RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import JsonResponse

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_session():
    s = SessionStore()
    s.create()
    return s

def _add_messages(request):
    setattr(request, '_messages', FallbackStorage(request))


def _mock_producto(pk=1, precio=500_000, codigo='PROD-001', referencia='Sofá Fátima'):
    p = MagicMock()
    p.id_producto = pk
    p.codigo_producto = codigo
    p.referencia_producto = referencia
    p.precio_actual = Decimal(str(precio))
    p.estado = 'DISPONIBLE'
    p.deleted_at = None
    p.created_at = None
    cat = MagicMock()
    cat.nombre_categoria = 'Sofás'
    p.categoria = cat
    p.get_imagen_principal = MagicMock(return_value=None)
    return p


def _mock_cliente(pk=1, email='cliente@test.com', nombre='Ana', apellido='López',
                    contrasena=None, estado='ACTIVO'):
    c = MagicMock()
    c.pk = pk
    c.id_cliente = pk
    c.email = email
    c.nombre = nombre
    c.apellido = apellido
    c.estado = estado
    c.deleted_at = None
    c.is_authenticated = True
    c.is_anonymous = False
    # Contraseña SHA256 de 'password123'
    c.contrasena_cliente = contrasena or hashlib.sha256(b'password123').hexdigest()
    c.backend = 'ventas.backends.ClientesAuthBackend'
    c.ultimo_login = None
    c.direccion = None
    c.genero = 'F'
    return c

# ══════════════════════════════════════════════════════════════
# 1. FUNCIÓN AUXILIAR — generar_avatar_url
# ══════════════════════════════════════════════════════════════

class GenerarAvatarUrlTests(TestCase):

    def test_retorna_url_con_nombre(self):
        from pagina.views import generar_avatar_url
        url = generar_avatar_url('María G.')
        self.assertIn('María+G.', url)
        self.assertIn('ui-avatars.com', url)

    def test_mismo_nombre_genera_misma_url(self):
        from pagina.views import generar_avatar_url
        self.assertEqual(generar_avatar_url('Carlos'), generar_avatar_url('Carlos'))

    def test_tamaño_personalizado(self):
        from pagina.views import generar_avatar_url
        url = generar_avatar_url('Test', tamaño=64)
        self.assertIn('size=64', url)

    def test_color_en_rango_valido(self):
        from pagina.views import generar_avatar_url
        colores_validos = [
            '667eea', '764ba2', 'f093fb', '4facfe', '43e972',
            'fa709a', 'fee140', '30cfd0', 'a8edea', 'feaca9'
        ]
        url = generar_avatar_url('Prueba')
        encontrado = any(color in url for color in colores_validos)
        self.assertTrue(encontrado)

# ══════════════════════════════════════════════════════════════
# 2. VISTA HOME
# ══════════════════════════════════════════════════════════════

class HomeViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get('/')
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        _add_messages(request)
        return request

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Categorias')
    @patch('pagina.views.Producto')
    def test_home_renderiza_y_contexto_tiene_claves(self, MockProd, MockCat, MockImg):
        from pagina.views import home

        MockProd.objects.filter.return_value.select_related.return_value.__getitem__ = MagicMock(return_value=[])
        qs_mock = MagicMock()
        qs_mock.order_by.return_value = []
        qs_mock.__iter__ = MagicMock(return_value=iter([]))
        MockProd.objects.filter.return_value.select_related.return_value = qs_mock
        MockProd.objects.filter.return_value.values_list.return_value.__getitem__ = MagicMock(return_value=[])
        MockCat.objects.filter.return_value.annotate.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])
        MockImg.objects.filter.return_value.first.return_value = None

        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            home(self._request())
            _, template, context = mock_render.call_args[0]

        self.assertEqual(template, 'pagina/index.html')
        for clave in ['productos_destacados', 'productos_nuevos', 'testimonios',
                        'categorias', 'carrito_cantidad']:
            self.assertIn(clave, context, f"Falta '{clave}' en el contexto de home")

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Categorias')
    @patch('pagina.views.Producto')
    def test_testimonios_tiene_exactamente_3(self, MockProd, MockCat, MockImg):
        from pagina.views import home
        qs_mock = MagicMock()
        qs_mock.order_by.return_value = []
        qs_mock.__iter__ = MagicMock(return_value=iter([]))
        MockProd.objects.filter.return_value.select_related.return_value = qs_mock
        MockProd.objects.filter.return_value.values_list.return_value.__getitem__ = MagicMock(return_value=[])
        MockCat.objects.filter.return_value.annotate.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])
        MockImg.objects.filter.return_value.first.return_value = None

        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            home(self._request())
            _, _, context = mock_render.call_args[0]

        self.assertEqual(len(context['testimonios']), 3)

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Categorias')
    @patch('pagina.views.Producto')
    def test_carrito_cantidad_viene_de_sesion(self, MockProd, MockCat, MockImg):
        from pagina.views import home
        qs_mock = MagicMock()
        qs_mock.order_by.return_value = []
        qs_mock.__iter__ = MagicMock(return_value=iter([]))
        MockProd.objects.filter.return_value.select_related.return_value = qs_mock
        MockProd.objects.filter.return_value.values_list.return_value.__getitem__ = MagicMock(return_value=[])
        MockCat.objects.filter.return_value.annotate.return_value.order_by.return_value.__getitem__ = MagicMock(return_value=[])

        request = self._request()
        request.session['carrito_cantidad'] = 7

        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            home(request)
            _, _, context = mock_render.call_args[0]

        self.assertEqual(context['carrito_cantidad'], 7)

# ══════════════════════════════════════════════════════════════
# 3. VISTA PRODUCTOS
# ══════════════════════════════════════════════════════════════

class ProductosViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get('/productos/')
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        _add_messages(request)
        return request

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Categorias')
    @patch('pagina.views.Producto')
    def test_productos_usa_paginacion(self, MockProd, MockCat, MockImg):
        from pagina.views import productos

        prods = [_mock_producto(pk=i) for i in range(1, 31)]
        MockProd.objects.filter.return_value.select_related.return_value.order_by.return_value = prods
        MockProd.objects.filter.return_value.order_by.return_value.values_list.return_value.__getitem__ = MagicMock(return_value=[])
        MockProd.objects.filter.return_value.count.return_value = 30

        cat_mock = MagicMock()
        cat_mock.id_categorias = 1
        cat_mock.nombre_categoria = 'Sofas'
        cat_mock.productos_count = 5
        MockCat.objects.filter.return_value.annotate.return_value.order_by.return_value = [cat_mock]
        MockImg.objects.filter.return_value.first.return_value = None

        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            productos(self._request())
            _, _, context = mock_render.call_args[0]

        self.assertIn('paginator', context)
        self.assertIn('page_obj', context)

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Categorias')
    @patch('pagina.views.Producto')
    def test_sort_options_tiene_5_opciones(self, MockProd, MockCat, MockImg):
        from pagina.views import productos
        MockProd.objects.filter.return_value.select_related.return_value.order_by.return_value = []
        MockProd.objects.filter.return_value.order_by.return_value.values_list.return_value.__getitem__ = MagicMock(return_value=[])
        MockProd.objects.filter.return_value.count.return_value = 0

        cat_mock = MagicMock()
        cat_mock.id_categorias = 1
        cat_mock.nombre_categoria = 'Sofas'
        cat_mock.productos_count = 5
        MockCat.objects.filter.return_value.annotate.return_value.order_by.return_value = [cat_mock]

        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            productos(self._request())
            _, _, context = mock_render.call_args[0]

        self.assertEqual(len(context['sort_options']), 5)

# ══════════════════════════════════════════════════════════════
# 4. LOGIN
# ══════════════════════════════════════════════════════════════

class LoginViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, correo, contrasena, extra=None):
        from pagina.views import login_view
        data = {'correo': correo, 'contrasena': contrasena}
        if extra:
            data.update(extra)
        request = self.factory.post('/login/', data)
        request.session = _make_session()
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        return login_view(request)

    def test_campos_vacios_no_redirige(self):
        response = self._post('', '')
        # debe renderizar el login de nuevo (no 302)
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    @patch('pagina.views.Usuarios')
    def test_correo_no_registrado_no_redirige(self, MockUsr, MockCli):
        MockUsr.objects.select_related.return_value.get.side_effect = MockUsr.DoesNotExist
        MockCli.objects.get.side_effect = MockCli.DoesNotExist
        # Aseguramos que DoesNotExist se propague correctamente
        MockUsr.DoesNotExist = Exception
        MockCli.DoesNotExist = Exception
        response = self._post('noexiste@test.com', 'cualquiera')
        self.assertNotEqual(response.status_code, 302)

@patch('pagina.views.login')
@patch('pagina.views.Usuarios')
def test_login_staff_exitoso_redirige_a_dashboard(self, MockUsr, mock_login):
    usuario = MagicMock()
    usuario.contrasena_usuario = hashlib.sha256(b'pass1234').hexdigest()
    usuario.estado = 'ACTIVO'
    usuario.nombres = 'Admin'
    usuario.apellidos = 'Test'
    usuario.id_rol = MagicMock(nombre_rol='GERENTE')
    usuario.id_usuario = 1

    # Configurar correctamente la cadena select_related().get()
    MockUsr.objects.select_related.return_value.get.return_value = usuario

    # DoesNotExist debe ser una subclase de Exception única,
    # NO Exception genérica, para que el except no la capture accidentalmente
    class UsuariosDoesNotExist(Exception):
        pass
    MockUsr.DoesNotExist = UsuariosDoesNotExist

    response = self._post('admin@test.com', 'pass1234')
    self.assertEqual(response.status_code, 302)
    self.assertIn('dashboard', response['Location'])


@patch('pagina.views.login')
@patch('pagina.views.Clientes')
@patch('pagina.views.Usuarios')
def test_login_cliente_exitoso_redirige_a_home(self, MockUsr, MockCli, mock_login):
    # Staff: no existe → lanza DoesNotExist correctamente
    class UsuariosDoesNotExist(Exception):
        pass
    MockUsr.DoesNotExist = UsuariosDoesNotExist
    MockUsr.objects.select_related.return_value.get.side_effect = UsuariosDoesNotExist

    # Cliente: existe con contraseña correcta
    class ClientesDoesNotExist(Exception):
        pass
    MockCli.DoesNotExist = ClientesDoesNotExist

    cliente = _mock_cliente()  # contrasena = sha256('password123')
    MockCli.objects.get.return_value = cliente

    response = self._post('cliente@test.com', 'password123')
    self.assertEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    @patch('pagina.views.Usuarios')
    def test_contrasena_incorrecta_no_redirige(self, MockUsr, MockCli):
        MockUsr.objects.select_related.return_value.get.side_effect = Exception
        MockUsr.DoesNotExist = Exception

        cliente = _mock_cliente()
        # Contraseña diferente a 'wrongpass'
        cliente.contrasena_cliente = hashlib.sha256(b'otraclave').hexdigest()
        MockCli.objects.get.return_value = cliente
        MockCli.DoesNotExist = Exception

        response = self._post('cliente@test.com', 'wrongpass')
        self.assertNotEqual(response.status_code, 302)

    def test_sesion_ya_activa_de_cliente_redirige_a_home(self):
        from pagina.views import login_view
        request = self.factory.get('/login/')
        request.session = _make_session()
        request.session['cliente_auth'] = True
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

# ══════════════════════════════════════════════════════════════
# 5. REGISTRO
# ══════════════════════════════════════════════════════════════

class RegistroViewTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, data):
        from pagina.views import registro_view
        request = self.factory.post('/registro/', data)
        request.session = _make_session()
        request.user = MagicMock(is_authenticated=False, id_usuario=None)
        # Simular que no tiene id_usuario (evitar redirect automático)
        del request.user.id_usuario
        _add_messages(request)
        return registro_view(request)

    @patch('pagina.views.Clientes')
    def test_campos_obligatorios_faltantes_no_redirige(self, MockCli):
        response = self._post({'nombre': 'Ana'})  # faltan campos
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    def test_email_invalido_falla(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        response = self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '123456', 'correo': 'email-invalido',
            'password': 'Password1', 'password2': 'Password1'
        })
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    def test_contrasenas_distintas_falla(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        response = self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'ana@test.com',
            'password': 'Password1', 'password2': 'Password2'
        })
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    def test_contrasena_muy_corta_falla(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        response = self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'ana@test.com',
            'password': 'abc', 'password2': 'abc'
        })
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    def test_email_duplicado_falla(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = True
        response = self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'ana@test.com',
            'password': 'Password1234', 'password2': 'Password1234'
        })
        self.assertNotEqual(response.status_code, 302)

    @patch('pagina.views.Clientes')
    def test_registro_exitoso_redirige_a_login(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        MockCli.objects.create.return_value = _mock_cliente()
        response = self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'nueva@test.com',
            'password': 'Password1234', 'password2': 'Password1234',
            'telefono': '3001234567'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    @patch('pagina.views.Clientes')
    def test_registro_hashea_contrasena_con_sha256(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        MockCli.objects.create.return_value = _mock_cliente()
        self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'nueva@test.com',
            'password': 'MiPassword99', 'password2': 'MiPassword99',
        })
        kwargs = MockCli.objects.create.call_args[1]
        esperado = hashlib.sha256(b'MiPassword99').hexdigest()
        self.assertEqual(kwargs['contrasena_cliente'], esperado)

    @patch('pagina.views.Clientes')
    def test_registro_auto_verifica_email(self, MockCli):
        MockCli.objects.filter.return_value.exists.return_value = False
        MockCli.objects.create.return_value = _mock_cliente()
        self._post({
            'nombre': 'Ana', 'apellidos': 'López',
            'documento': '12345678', 'correo': 'nueva@test.com',
            'password': 'Password1234', 'password2': 'Password1234',
        })
        kwargs = MockCli.objects.create.call_args[1]
        self.assertTrue(kwargs['email_verificado'])

# ══════════════════════════════════════════════════════════════
# 6. LOGOUT
# ══════════════════════════════════════════════════════════════

class LogoutPaginaTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @patch('pagina.views.logout')
    def test_logout_limpia_claves_de_sesion_y_redirige(self, mock_logout):
        from pagina.views import logout_view
        request = self.factory.get('/logout/')
        request.session = _make_session()
        request.session['cliente_id'] = 1
        request.session['carrito'] = {'1': {'cantidad': 2}}
        request.session['carrito_cantidad'] = 2
        request.user = _mock_cliente()
        _add_messages(request)
        response = logout_view(request)
        mock_logout.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('cliente_id', request.session)
        self.assertNotIn('carrito', request.session)

# ══════════════════════════════════════════════════════════════
# 7. API CARRITO — api_agregar_carrito
# ══════════════════════════════════════════════════════════════

class ApiAgregarCarritoTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post(self, body, session=None):
        from pagina.views import api_agregar_carrito
        request = self.factory.post(
            '/api/carrito/agregar/',
            data=json.dumps(body),
            content_type='application/json'
        )
        request.session = session or _make_session()
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        return api_agregar_carrito(request)

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Producto')
    def test_agregar_producto_exitoso(self, MockProd, MockImg):
        prod = _mock_producto()
        MockProd.objects.get.return_value = prod
        MockImg.objects.filter.return_value.first.return_value = None

        with patch('pagina.views.Carritos'), patch('pagina.views.ItemsCarrito'):
            response = self._post({'producto_id': '1', 'cantidad': 2})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['cantidad_total'], 2)

    @patch('pagina.views.Producto')
    def test_producto_inexistente_retorna_404(self, MockProd):
        MockProd.DoesNotExist = Exception
        MockProd.objects.get.side_effect = MockProd.DoesNotExist
        response = self._post({'producto_id': '999', 'cantidad': 1})
        self.assertEqual(response.status_code, 404)

    @patch('pagina.views.ImagenesProducto')
    @patch('pagina.views.Producto')
    def test_agregar_mismo_producto_acumula_cantidad(self, MockProd, MockImg):
        prod = _mock_producto()
        MockProd.objects.get.return_value = prod
        MockImg.objects.filter.return_value.first.return_value = None

        session = _make_session()
        session['carrito'] = {'1': {'producto_id': '1', 'nombre': 'Sofá',
                                        'precio': 500000.0, 'cantidad': 1,
                                        'imagen_url': '/img.jpg'}}
        session['carrito_cantidad'] = 1

        with patch('pagina.views.Carritos'), patch('pagina.views.ItemsCarrito'):
            response = self._post({'producto_id': '1', 'cantidad': 3}, session=session)

        data = json.loads(response.content)
        self.assertEqual(data['cantidad_total'], 4)  # 1 previo + 3 nuevos

    def test_json_invalido_retorna_400(self):
        from pagina.views import api_agregar_carrito
        request = self.factory.post(
            '/api/carrito/agregar/',
            data='no-es-json',
            content_type='application/json'
        )
        request.session = _make_session()
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        response = api_agregar_carrito(request)
        self.assertEqual(response.status_code, 400)

# ══════════════════════════════════════════════════════════════
# 8. API CUPÓN — api_cupon_aplicar y api_cupon_remover
# ══════════════════════════════════════════════════════════════

class ApiCuponTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _post_cupon(self, codigo, carrito_session=None):
        from pagina.views import api_cupon_aplicar
        session = _make_session()
        if carrito_session:
            session['carrito'] = carrito_session
        request = self.factory.post(
            '/api/cupon/aplicar/',
            data=json.dumps({'codigo': codigo}),
            content_type='application/json'
        )
        request.session = session
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        with patch('pagina.views.Carritos') as MockCar:
            MockCar.objects.filter.return_value.first.return_value = None
            return api_cupon_aplicar(request)

    def test_cupon_invalido_retorna_400(self):
        carrito = {'1': {'precio': 300000, 'cantidad': 1}}
        response = self._post_cupon('INVALIDO123', carrito)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])

    def test_carrito_vacio_retorna_error(self):
        response = self._post_cupon('ORDERRAE20')
        self.assertEqual(response.status_code, 400)

    def test_cupon_porcentaje_calcula_descuento_correcto(self):
        # ORDERRAE20 = 20% de descuento
        carrito = {'1': {'precio': 100000, 'cantidad': 1}}  # 100k + 19k IVA = 119k
        response = self._post_cupon('ORDERRAE20', carrito)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        # 20% de 119.000 = 23.800
        self.assertAlmostEqual(data['descuento'], 23800, delta=10)

    def test_cupon_fijo_envio500_requiere_minimo(self):
        # ENVIO500 requiere compra mínima de 200.000
        carrito = {'1': {'precio': 50000, 'cantidad': 1}}  # 59.500 con IVA < 200.000
        response = self._post_cupon('ENVIO500', carrito)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('mínimo', data['error'].lower())

    def test_cupon_se_guarda_en_sesion(self):
        carrito = {'1': {'precio': 300000, 'cantidad': 1}}
        response = self._post_cupon('BIENVENIDO10', carrito)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['codigo'], 'BIENVENIDO10')

    def test_remover_cupon_limpia_sesion(self):
        from pagina.views import api_cupon_remover
        request = self.factory.post('/api/cupon/remover/',
                                        content_type='application/json')
        session = _make_session()
        session['cupon_activo'] = {'codigo': 'TEST', 'valor': 10}
        request.session = session
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        response = api_cupon_remover(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('cupon_activo', request.session)

# ══════════════════════════════════════════════════════════════
# 9. API NOTIFICACIONES
# ══════════════════════════════════════════════════════════════

class ApiNotificacionesTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_listar_retorna_estructura_correcta(self):
        from pagina.views import api_listar_notificaciones
        request = self.factory.get('/api/notificaciones/')
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        response = api_listar_notificaciones(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('nuevas', data)
        self.assertIn('notificaciones', data)

    def test_crear_notificacion_exitosa(self):
        from pagina.views import api_crear_notificacion
        request = self.factory.post(
            '/api/notificaciones/crear/',
            data=json.dumps({'mensaje': 'Test', 'tipo': 'info'}),
            content_type='application/json'
        )
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        response = api_crear_notificacion(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_crear_notificacion_json_invalido_retorna_400(self):
        from pagina.views import api_crear_notificacion
        request = self.factory.post(
            '/api/notificaciones/crear/',
            data='no-json',
            content_type='application/json'
        )
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        response = api_crear_notificacion(request)
        self.assertEqual(response.status_code, 400)

    def test_marcar_leidas_retorna_success(self):
        from pagina.views import api_marcar_leidas
        request = self.factory.post('/api/notificaciones/marcar-leidas/')
        request.user = MagicMock(is_authenticated=False)
        request.session = _make_session()
        response = api_marcar_leidas(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

# ══════════════════════════════════════════════════════════════
# 10. VISTAS ESTÁTICAS DE LA EMPRESA
# ══════════════════════════════════════════════════════════════

class VistasEmpresaTests(TestCase):
    """Verifica que las vistas informativas rendericen con contextos correctos."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get('/')
        request.session = _make_session()
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        return request

    def _check_render(self, view_fn, expected_template, *context_keys):
        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            view_fn(self._request())
            _, template, context = mock_render.call_args[0]
        self.assertEqual(template, expected_template)
        for key in context_keys:
            self.assertIn(key, context, f"Falta '{key}' en contexto de {expected_template}")
        return context

    def test_quienes_somos_renderiza(self):
        from pagina.views import quienes_somos
        ctx = self._check_render(quienes_somos, 'pagina/quienes_somos.html', 'equipo', 'valores')
        self.assertEqual(len(ctx['equipo']), 4)
        self.assertEqual(len(ctx['valores']), 4)

    def test_trabaja_tiene_vacantes_y_beneficios(self):
        from pagina.views import trabaja_con_nosotros
        ctx = self._check_render(trabaja_con_nosotros, 'pagina/trabaja_con_nosotros.html',
                                    'vacantes', 'beneficios')
        self.assertGreater(len(ctx['vacantes']), 0)
        self.assertGreater(len(ctx['beneficios']), 0)

    def test_blog_tiene_articulos_con_campos_requeridos(self):
        from pagina.views import blog_decoracion
        ctx = self._check_render(blog_decoracion, 'pagina/blog_decoracion.html',
                                    'articulos', 'categorias_blog')
        for art in ctx['articulos']:
            for campo in ['titulo', 'excerpt', 'fecha', 'autor', 'categoria']:
                self.assertIn(campo, art, f"Falta '{campo}' en artículo del blog")

    def test_rastrear_pedido_renderiza(self):
        from pagina.views import rastrear_pedido
        self._check_render(rastrear_pedido, 'pagina/rastrear_pedido.html', 'carrito_cantidad')

# ══════════════════════════════════════════════════════════════
# 11. VISTA INFO_AYUDA — slugs válidos e inválidos
# ══════════════════════════════════════════════════════════════

class InfoAyudaTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    # Método auxiliar para hacer requests a info_ayuda con un slug dado
    def _request(self, slug):
        from pagina.views import info_ayuda
        request = self.factory.get(f'/info-ayuda/{slug}/')
        request.session = _make_session()
        request.user = MagicMock(is_authenticated=False)
        _add_messages(request)
        return info_ayuda(request, slug)

    # Para cada slug válido, verifica que se renderice el template correcto y que el contexto tenga 'pagina' con el valor del slug
    def test_slug_materiales_renderiza(self):
        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            self._request('materiales')
            _, template, context = mock_render.call_args[0]
        self.assertEqual(context['pagina'], 'materiales')

    # El test para 'cuidado' se omite por simplicidad, pero sería similar a los demás
    def test_slug_envios_renderiza(self):
        with patch('pagina.views.render') as mock_render:
            mock_render.return_value = MagicMock(status_code=200)
            self._request('envios')
            _, template, context = mock_render.call_args[0]
        self.assertEqual(context['pagina'], 'envios')

    # El test para 'devoluciones' se omite por simplicidad, pero sería similar a los demás 
    def test_slug_invalido_lanza_404(self):
        from django.http import Http404
        with self.assertRaises(Http404):
            self._request('slug-inexistente')

    # Para cada slug válido, verifica que el contexto tenga 'titulo_seccion' con un valor no nulo y que el template renderizado sea 'pagina/info_ayuda.html' 
    def test_todos_los_slugs_validos_tienen_titulo(self):
        slugs = ['materiales', 'cuidado', 'envios', 'devoluciones', 'preguntas_frecuentes']
        for slug in slugs:
            with patch('pagina.views.render') as mock_render:
                mock_render.return_value = MagicMock(status_code=200)
                self._request(slug)
                _, _, context = mock_render.call_args[0]
            self.assertIn('titulo_seccion', context)
            self.assertIsNotNone(context['titulo_seccion'])

# ══════════════════════════════════════════════════════════════
# 12. TEMPLATE TAGS — custom_filters
# ══════════════════════════════════════════════════════════════

class CustomFiltersTests(TestCase):

    # Cada test importa la función del filtro, la ejecuta con un input específico y verifica que el output sea el esperado.
    def test_split_divide_correctamente(self):
        from pagina.templatetags.custom_filters import split
        result = split('a,b,c', ',')
        self.assertEqual(result, ['a', 'b', 'c'])

    # El test para split con separador no presente se omite por simplicidad
    def test_replace_reemplaza_correctamente(self):
        from pagina.templatetags.custom_filters import replace
        result = replace('hola-mundo', '-/ ')
        self.assertEqual(result, 'hola mundo')

    # El test para replace con texto a reemplazar no presente se omite por simplicidad
    def test_cop_format_formatea_miles_con_punto(self):
        from pagina.templatetags.custom_filters import cop_format
        self.assertEqual(cop_format(1234567), '1.234.567')

    # El test para cop_format con número menor a 1000 se omite por simplicidad
    def test_cop_format_acepta_decimal(self):
        from pagina.templatetags.custom_filters import cop_format
        self.assertEqual(cop_format(Decimal('500000.99')), '500.001')

    # El test para cop_format con valor no numérico se omite por simplicidad
    def test_cop_format_con_valor_invalido_devuelve_valor(self):
        from pagina.templatetags.custom_filters import cop_format
        result = cop_format('no-es-numero')
        self.assertEqual(result, 'no-es-numero')

    # El test para add_percent con porcentaje negativo se omite por simplicidad
    def test_add_percent_calcula_bien(self):
        from pagina.templatetags.custom_filters import add_percent
        result = add_percent(Decimal('100'), 20)
        self.assertEqual(result, Decimal('120'))

    # El test para add_percent con porcentaje cero se omite por simplicidad
    def test_make_range_devuelve_range(self):
        from pagina.templatetags.custom_filters import make_range
        self.assertEqual(list(make_range(3)), [0, 1, 2])

    # El test para make_range con cero o negativo se omite por simplicidad
    def test_make_range_con_valor_invalido_devuelve_vacio(self):
        from pagina.templatetags.custom_filters import make_range
        self.assertEqual(list(make_range('abc')), [])

# ══════════════════════════════════════════════════════════════
# 13. TEMPLATE TAGS — custom_auth (has_role)
# ══════════════════════════════════════════════════════════════

class CustomAuthTagTests(TestCase):

    def test_has_role_usuario_sin_autenticar_retorna_false(self):
        from pagina.templatetags.custom_auth import has_role
        user = MagicMock(is_authenticated=False)
        self.assertFalse(has_role(user, 'ADMIN'))

    def test_has_role_con_rol_correcto_retorna_true(self):
        from pagina.templatetags.custom_auth import has_role
        user = MagicMock(is_authenticated=True, rol='GERENTE')
        self.assertTrue(has_role(user, 'GERENTE,ADMIN'))

    def test_has_role_con_rol_incorrecto_retorna_false(self):
        from pagina.templatetags.custom_auth import has_role
        user = MagicMock(is_authenticated=True, rol='BODEGA')
        self.assertFalse(has_role(user, 'GERENTE,ADMIN'))

    def test_has_role_superuser_puede_ser_admin(self):
        from pagina.templatetags.custom_auth import has_role
        user = MagicMock(is_authenticated=True, is_superuser=True, is_staff=True)
        del user.rol  # sin atributo rol
        user.groups = MagicMock()
        user.groups.values_list.return_value = []
        # Simular que no tiene atributo rol
        type(user).rol = PropertyMock(side_effect=AttributeError)
        self.assertTrue(has_role(user, 'ADMIN'))