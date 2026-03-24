# usuarios/urls.py
from django.urls import path
from .views import (
    # Login/Logout
    login_view, logout_view,
    # Roles
    RolListView, RolCreateView, RolUpdateView, RolDeleteView, RolDetailView,
    # Usuarios
    UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView, UsuarioDetailView,
)

app_name = 'usuarios'

urlpatterns = [
    # Login/Logout
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Roles
    path('roles/', RolListView.as_view(), name='rol_list'),
    path('roles/nuevo/', RolCreateView.as_view(), name='rol_create'),
    path('roles/<int:pk>/', RolDetailView.as_view(), name='rol_detail'),
    path('roles/<int:pk>/editar/', RolUpdateView.as_view(), name='rol_update'),
    path('roles/<int:pk>/eliminar/', RolDeleteView.as_view(), name='rol_delete'),
    
    # Usuarios
    path('usuarios/', UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/nuevo/', UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/', UsuarioDetailView.as_view(), name='usuario_detail'),
    path('usuarios/<int:pk>/editar/', UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/<int:pk>/eliminar/', UsuarioDeleteView.as_view(), name='usuario_delete'),
]