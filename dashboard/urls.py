# dashboard/urls.py
from django.urls import path
from .views import (
    dashboard_redirect, 
    DashboardView,  # Gerente
    dashboard_asesor, 
    dashboard_logistica, 
    dashboard_bodega,
    logout_view
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
]