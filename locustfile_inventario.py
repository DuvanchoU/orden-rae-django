"""
Pruebas de carga para el módulo INVENTARIO - ORDEN R.A.E.
SENA ADSO - Proyecto Académico
"""

from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import random
from datetime import datetime

# =============================================================================
# IDs REALES DE LA BASE DE DATOS (20 registros de inventario)
# =============================================================================

# Productos que SÍ existen en inventario (según tu screenshot)
VALID_PRODUCT_IDS = [1, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 18, 19, 21, 22]

# IDs de inventario existentes (del 1 al 20 aproximadamente)
VALID_INVENTARIO_IDS = list(range(1, 21))  # [1, 2, 3, ..., 20]

# Bodegas existentes (según la BD)
VALID_BODEGA_IDS = [1, 2, 3, 4, 5, 6] # Principales bodegas

# =============================================================================
# CLASES DE USUARIO
# =============================================================================

class GerenteInventarioUser(HttpUser):
    """
    Usuario: Gerente con acceso completo al módulo Inventario
    """
    wait_time = between(4, 8)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        """Login con manejo de CSRF"""
        try:
            login_page = self.client.get("/login/")
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input['value'] if csrf_input else self.client.cookies.get('csrftoken')
            
            login_data = {
                'correo': 'gerente@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            headers = {'Referer': 'http://127.0.0.1:8000/login/'}
            response = self.client.post("/login/", data=login_data, headers=headers)
            print(f"🔐 Login gerente: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Login falló: {e}")
    
    @task(4)
    def listar_productos(self):
        """Consulta listado de productos con filtros"""
        filtros = [
            '',
            '?estado=DISPONIBLE',
            '?estado=AGOTADO',
            '?busqueda=CUN',
            '?busqueda=CAMA',
        ]
        filtro = random.choice(filtros)
        self.client.get(f"/inventario/productos/{filtro}")
    
    @task(3)
    def ver_detalle_producto(self):
        """Ve detalle de un producto existente"""
        producto_id = random.choice(VALID_PRODUCT_IDS)
        response = self.client.get(f"/inventario/productos/{producto_id}/")
        if response.status_code == 404:
            print(f"⚠️  Producto {producto_id} no encontrado (posible soft delete)")
    
    @task(2)
    def listar_inventario(self):
        """Consulta stock por bodega"""
        filtros = [
            '',
            '?estado=DISPONIBLE',
            '?estado=COMPROMETIDO',
            '?estado=AGOTADO',
            f'?bodega={random.choice(VALID_BODEGA_IDS)}',
        ]
        filtro = random.choice(filtros)
        self.client.get(f"/inventario/stock/{filtro}")
    
    @task(2)
    def ver_detalle_inventario(self):
        """Ve detalle de un registro de inventario existente"""
        inventario_id = random.choice(VALID_INVENTARIO_IDS)
        response = self.client.get(f"/inventario/inventario/{inventario_id}/")
        if response.status_code == 404:
            print(f"⚠️  Inventario {inventario_id} no encontrado")
    
    @task(1)
    def listar_proveedores(self):
        """Consulta directorio de proveedores"""
        self.client.get("/inventario/proveedores/?estado=ACTIVO")


class AsesorInventarioUser(HttpUser):
    """
    Usuario: Asesor Comercial - Acceso de solo lectura
    """
    wait_time = between(5, 10)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        """Login asesor"""
        try:
            login_page = self.client.get("/login/")
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input['value'] if csrf_input else self.client.cookies.get('csrftoken')
            
            login_data = {
                'correo': 'asesor@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            headers = {'Referer': 'http://127.0.0.1:8000/login/'}
            self.client.post("/login/", data=login_data, headers=headers)
        except:
            pass
    
    @task(5)
    def buscar_producto(self):
        """Búsqueda frecuente de productos existentes"""
        busquedas = ['CUN', 'CAMA', 'BUT', 'POL', 'MEC', '']
        termino = random.choice(busquedas)
        self.client.get(f"/inventario/productos/?busqueda={termino}")
    
    @task(3)
    def consultar_stock(self):
        """Verifica disponibilidad de stock"""
        self.client.get("/inventario/stock/?estado=DISPONIBLE")
    
    @task(2)
    def ver_producto_aleatorio(self):
        """Ve detalle de producto aleatorio existente"""
        producto_id = random.choice(VALID_PRODUCT_IDS)
        self.client.get(f"/inventario/productos/{producto_id}/")


class BodegaUser(HttpUser):
    """
    Usuario: Auxiliar de Bodega - Gestión operativa
    """
    wait_time = between(3, 7)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        """Login bodega"""
        try:
            login_page = self.client.get("/login/")
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input['value'] if csrf_input else self.client.cookies.get('csrftoken')
            
            login_data = {
                'correo': 'bodega@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            headers = {'Referer': 'http://127.0.0.1:8000/login/'}
            self.client.post("/login/", data=login_data, headers=headers)
        except:
            pass
    
    @task(4)
    def listar_stock_bodega(self):
        """Consulta stock de bodega asignada"""
        bodega_id = random.choice([1, 2, 3])  # Principales
        self.client.get(f"/inventario/stock/?bodega={bodega_id}")
    
    @task(3)
    def ver_detalle_inventario(self):
        """Ve detalle de registro de inventario"""
        inventario_id = random.choice(VALID_INVENTARIO_IDS)
        self.client.get(f"/inventario/inventario/{inventario_id}/")
    
    @task(2)
    def filtrar_por_estado(self):
        """Filtra por estado de stock"""
        estados = ['DISPONIBLE', 'COMPROMETIDO', 'AGOTADO']
        estado = random.choice(estados)
        self.client.get(f"/inventario/stock/?estado={estado}")
    
    @task(1)
    def consultar_productos(self):
        """Lista productos disponibles"""
        self.client.get("/inventario/productos/?estado=DISPONIBLE")


class ReadOnlyUser(HttpUser):
    """
    Usuario sin autenticación - Acceso público
    """
    wait_time = between(6, 12)
    host = "http://127.0.0.1:8000"
    
    @task(3)
    def home_publica(self):
        self.client.get("/")
    
    @task(2)
    def productos_publicos(self):
        self.client.get("/productos/")
    
    @task(1)
    def login_page(self):
        self.client.get("/login/")


class StressTestInventario(HttpUser):
    """
    Pruebas de estrés intensivo
    """
    wait_time = between(0.5, 1.5)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        """Login rápido"""
        try:
            self.client.get("/login/")
            login_data = {
                'correo': 'gerente@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            self.client.post("/login/", data=login_data, allow_redirects=False)
        except:
            pass
    
    @task(3)
    def stress_listado_productos(self):
        self.client.get("/inventario/productos/")
    
    @task(3)
    def stress_listado_stock(self):
        self.client.get("/inventario/stock/")
    
    @task(2)
    def stress_detalle_producto(self):
        pk = random.choice(VALID_PRODUCT_IDS)
        self.client.get(f"/inventario/productos/{pk}/")
    
    @task(1)
    def stress_detalle_inventario(self):
        pk = random.choice(VALID_INVENTARIO_IDS)
        self.client.get(f"/inventario/inventario/{pk}/")


# =============================================================================
# EVENTOS
# =============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log de requests"""
    if exception:
        print(f"❌ ERROR [{request_type}] {name}: {exception}")
    elif response_time > 2000:
        print(f"⚠️  LENTO [{response_time:.0f}ms] {request_type} {name}")
    elif response_time > 500:
        print(f"🟡 MODERADO [{response_time:.0f}ms] {request_type} {name}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Inicio de pruebas"""
    print("\n" + "="*80)
    print("🚀 PRUEBAS DE CARGA - MÓDULO INVENTARIO")
    print("📦 ORDEN R.A.E. - Sistema ERP")
    print("="*80)
    print(f"🎯 Target: {environment.host}")
    print(f"📊 IDs de producto válidos: {len(VALID_PRODUCT_IDS)} ({VALID_PRODUCT_IDS})")
    print(f"📊 IDs de inventario válidos: {len(VALID_INVENTARIO_IDS)} (1-20)")
    print(f"⏰  Hora inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Resumen final"""
    stats = environment.stats
    total = stats.total.num_requests
    fails = stats.total.num_failures
    avg_rt = stats.total.avg_response_time
    rps = stats.total.current_rps
    
    print("\n" + "="*80)
    print("✅ PRUEBAS FINALIZADAS - RESUMEN INVENTARIO")
    print("="*80)
    print(f"📈 Total Requests: {total:,}")
    print(f"❌ Failures: {fails} ({fails/max(total,1)*100:.2f}%)")
    print(f"⏱️  Avg Response Time: {avg_rt:.2f}ms")
    print(f"⚡ RPS Promedio: {rps:.2f}")
    
    # Métricas por endpoint principal
    print("\n📊 Por endpoint principal:")
    for endpoint in ['/inventario/productos/', '/inventario/stock/', '/inventario/proveedores/']:
        e_stats = stats.get(endpoint, 'GET')
        if e_stats and e_stats.num_requests > 0:
            print(f"   • {endpoint}: {e_stats.num_requests} reqs, "
                  f"{e_stats.avg_response_time:.0f}ms avg, "
                  f"{e_stats.num_failures} fails")
    
    print("="*80 + "\n")


# =============================================================================
# EJECUCIÓN
# =============================================================================

# Comandos recomendados:
# 
# 1. Prueba normal (20 usuarios):
#    locust -f locustfile_inventario.py --host=http://127.0.0.1:8000
#
# 2. Prueba headless con exportación:
#    locust -f locustfile_inventario.py --headless -u 20 -r 5 -t 3m \
#      --csv=resultados_inventario --html=reporte_inventario.html
#
# 3. Estrés intensivo (50 usuarios):
#    locust -f locustfile_inventario.py --headless -u 50 -r 10 -t 2m StressTestInventario