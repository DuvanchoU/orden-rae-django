"""
Pruebas de carga para ORDEN R.A.E. - SENA ADSO
"""
from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup  # pip install beautifulsoup4
import re

class GerenteUser(HttpUser):
    """Usuario GERENTE - con manejo de CSRF"""
    wait_time = between(3, 7)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        """Login con extracción de CSRF token"""
        try:
            # 1. Obtener página de login para extraer CSRF token
            login_page = self.client.get("/login/")
            
            # 2. Extraer token CSRF del HTML
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input['value'] if csrf_input else None
            
            if not csrf_token:
                # Intentar extraer de cookies como fallback
                csrf_token = self.client.cookies.get('csrftoken')
            
            # 3. Preparar datos de login
            login_data = {
                'correo': 'gerente@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            # 4. Enviar POST con headers correctos
            headers = {'Referer': 'http://127.0.0.1:8000/login/'}
            response = self.client.post("/login/", data=login_data, headers=headers)
            
            print(f"🔐 Login gerente: {response.status_code} - Redirect: {response.headers.get('Location', 'N/A')}")
            
        except Exception as e:
            print(f"⚠️  Login gerente falló: {e}")
    
    @task(5)
    def dashboard_gerente(self):
        self.client.get("/dashboard/gerente/")
    
    @task(3)
    def perfil(self):
        self.client.get("/dashboard/perfil/")
    
    @task(2)
    def session_check(self):
        self.client.get("/dashboard/session-check/")


class AsesorUser(HttpUser):
    """Usuario ASESOR"""
    wait_time = between(4, 8)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
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
            response = self.client.post("/login/", data=login_data, headers=headers)
            print(f"🔐 Login asesor: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Login asesor falló: {e}")
    
    @task(4)
    def dashboard_asesor(self):
        self.client.get("/dashboard/asesor/")
    
    @task(3)
    def metricas_ventas(self):
        self.client.get("/dashboard/asesor/?filter=mes_actual")


class LogisticaUser(HttpUser):
    """Usuario LOGÍSTICA"""
    wait_time = between(3, 6)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
        try:
            login_page = self.client.get("/login/")
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            csrf_token = csrf_input['value'] if csrf_input else self.client.cookies.get('csrftoken')
            
            login_data = {
                'correo': 'logistica@ordenrae.com',
                'contrasena': 'Temporal123',
            }
            if csrf_token:
                login_data['csrfmiddlewaretoken'] = csrf_token
            
            headers = {'Referer': 'http://127.0.0.1:8000/login/'}
            response = self.client.post("/login/", data=login_data, headers=headers)
            print(f"🔐 Login logistica: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Login logistica falló: {e}")
    
    @task(5)
    def dashboard_logistica(self):
        self.client.get("/dashboard/logistica/")


class BodegaUser(HttpUser):
    """Usuario BODEGA"""
    wait_time = between(5, 10)
    host = "http://127.0.0.1:8000"
    
    def on_start(self):
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
            response = self.client.post("/login/", data=login_data, headers=headers)
            print(f"🔐 Login bodega: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Login bodega falló: {e}")
    
    @task(6)
    def dashboard_bodega(self):
        self.client.get("/dashboard/bodega/")


class DashboardOnlyUser(HttpUser):
    """
    Usuario que solo prueba endpoints GET del dashboard
    Útil si el login con CSRF es muy complejo para la prueba
    """
    wait_time = between(2, 5)
    host = "http://127.0.0.1:8000"
    
    @task(3)
    def dashboard_gerente(self):
        self.client.get("/dashboard/gerente/")
    
    @task(2)
    def dashboard_asesor(self):
        self.client.get("/dashboard/asesor/")
    
    @task(2)
    def dashboard_logistica(self):
        self.client.get("/dashboard/logistica/")
    
    @task(2)
    def dashboard_bodega(self):
        self.client.get("/dashboard/bodega/")
    
    @task(1)
    def home_publica(self):
        self.client.get("/")


# =============================================================================
# EVENTOS
# =============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        print(f"❌ ERROR [{request_type}] {name}: {exception}")
    elif response_time > 1000:
        print(f"⚠️  LENTO [{response_time}ms] {request_type} {name}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "="*80)
    print("🚀 PRUEBAS DE CARGA - ORDEN R.A.E.")
    print("="*80)
    print(f"📊 Target: {environment.host}")
    print(f"🔐 Login URL: /login/")
    print(f"🛡️  CSRF: Habilitado")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    print("\n" + "="*80)
    print("✅ PRUEBAS FINALIZADAS")
    print("="*80)
    print(f"📈 Total Requests: {stats.total.num_requests}")
    print(f"❌ Failures: {stats.total.num_failures} ({stats.total.num_failures/max(stats.total.num_requests,1)*100:.2f}%)")
    print(f"⏱️  Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"⚡ RPS: {stats.total.current_rps:.2f}")
    print("="*80 + "\n")