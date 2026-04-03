# dashboard/urls.py
from django.urls import path
from . import views
from .views import (
    dashboard_redirect, 
    DashboardView,  # Gerente
    dashboard_asesor, 
    dashboard_logistica, 
    dashboard_bodega,
    logout_view,
    perfil_view,          
    perfil_update_view,
    session_check,
) 

app_name = 'dashboard' 

urlpatterns = [
    path('', dashboard_redirect, name='dashboard_home'),
    path('redirect/', dashboard_redirect, name='dashboard_redirect'),
    
    
    # Dashboards por rol
    path('gerente/', DashboardView.as_view(), name='dashboard_gerente'),
    path('asesor/', dashboard_asesor, name='dashboard_asesor'),
    path('logistica/', dashboard_logistica, name='dashboard_logistica'),
    path('bodega/', dashboard_bodega, name='dashboard_bodega'),
    path('logout/', logout_view, name='logout'),

    # Perfil del usuario
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/actualizar/', views.perfil_update_view, name='perfil_update'),

    # Endpoint para verificar sesión activa (AJAX)
    path('session-check/', session_check, name='session_check'),
]