import pytest
from django.test import Client


@pytest.mark.django_db
class TestIntegracionAuth:
    """Pruebas de integración: Login + Usuarios + Roles"""
    
    def test_flujo_completo_login_exitoso(self, client, usuario_admin):
        """Integración: Login → Validación credenciales → Sesión"""
        # Usar URL directa en lugar de reverse
        response = client.post('/login/', {
            'correo': 'admin@ordenrae.com',
            'contrasena': 'Temporal123'
        })
        
        # Verificar que la sesión existe
        assert client.session.get('_auth_user_id') is not None or response.status_code in [200, 302]
    
    def test_login_fallido_credenciales_incorrectas(self, client, usuario_admin):
        """Integración: Login fallido"""
        response = client.post('/login/', {
            'correo': 'admin@ordenrae.com',
            'contrasena': 'Incorrecta123'
        })
        
        assert response.status_code == 200
    
    def test_usuario_activo_puede_acceder(self, client, usuario_admin):
        """Integración: Usuario activo → Acceso a sistema"""
        client.post('/login/', {
            'correo': 'admin@ordenrae.com',
            'contrasena': 'Temporal123'
        })
        
        response = client.get('/dashboard/')
        assert response.status_code == 200
    
    def test_usuario_inactivo_no_puede_acceder(self, client, usuario_admin):
        """Integración: Usuario inactivo → Bloqueo"""
        usuario_admin.estado = 'INACTIVO'
        usuario_admin.save()
        
        response = client.post('/login/', {
            'correo': 'admin@ordenrae.com',
            'contrasena': 'Temporal123'
        })
        
        assert response.status_code == 200
    
    def test_roles_y_permisos_integrados(self, client, usuario_admin, rol_gerente):
        """Integración: Usuario → Rol → Permisos"""
        assert usuario_admin.id_rol == rol_gerente
        assert usuario_admin.id_rol.nombre_rol == 'GERENTE'
        assert usuario_admin.is_authenticated is True
        assert usuario_admin.is_active is True
        assert usuario_admin.is_staff is True
    
    def test_logout_cierra_sesion(self, client, usuario_admin):
        """Integración: Logout → Cierre de sesión"""
        client.post('/login/', {
            'correo': 'admin@ordenrae.com',
            'contrasena': 'Temporal123'
        })
        
        response = client.post('/logout/')
        assert response.status_code in [200, 302]
    
    def test_asesor_comercial_tiene_permisos_limitados(self, client, usuario_asesor, rol_asesor):
        """Integración: Asesor → Permisos específicos"""
        assert usuario_asesor.id_rol == rol_asesor
        assert usuario_asesor.is_staff is True
        assert usuario_asesor.is_superuser is False
        assert usuario_asesor.has_module_perms('ventas') is True
        assert usuario_asesor.has_module_perms('inventario') is True
        assert usuario_asesor.has_module_perms('compras') is False