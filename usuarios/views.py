from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.views.generic import View
import time

# Importar modelos y formularios
from .models import Usuarios, RolesOld
from .forms import UsuarioForm, UsuarioUpdateForm, RolForm
from django.contrib import messages

# Importar funciones de utilidad para manejo de intentos de login y bloqueo
from .utils import (
    get_login_attempts, 
    increment_login_attempts, 
    reset_login_attempts,
    is_login_blocked,
    block_login,
    get_client_ip
)

# Vistas de Autenticación Personalizada con Rate Limiting y Protección de Caché

@never_cache
def login_view(request):
    return redirect('/pagina/login/')


@never_cache  # Previene caché en logout
def logout_view(request):
    """
    Cierra la sesión del usuario y limpia todo.
    """
    # Limpiar TODA la sesión
    request.session.flush()
    return redirect('/pagina/login/?logged_out=1')

# =============================================================================
# === VISTAS DE ROLES ===
# =============================================================================

@method_decorator(never_cache, name='dispatch')
class RolListView(ListView):
    model = RolesOld
    template_name = 'usuarios/rol_list.html'
    context_object_name = 'roles'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        busqueda = self.request.GET.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(nombre_rol__icontains=busqueda) |
                Q(descripcion__icontains=busqueda)
            )
        return queryset.order_by('nombre_rol')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Lista de Roles'
        return context


@method_decorator(never_cache, name='dispatch')
class RolCreateView(CreateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Rol'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Rol creado exitosamente')
        return response


@method_decorator(never_cache, name='dispatch')
class RolUpdateView(UpdateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Rol'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Rol actualizado exitosamente')
        return response


@method_decorator(never_cache, name='dispatch')
class RolDeleteView(DeleteView):
    model = RolesOld
    template_name = 'usuarios/rol_confirm_delete.html'
    success_url = reverse_lazy('usuarios:rol_list')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Rol eliminado exitosamente')
        return response


@method_decorator(never_cache, name='dispatch')
class RolDetailView(DetailView):
    model = RolesOld
    template_name = 'usuarios/rol_detail.html'
    context_object_name = 'rol'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rol = self.get_object()
        context['titulo'] = f'Detalle: {rol.nombre_rol}'
        context['usuarios_con_rol'] = Usuarios.objects.filter(id_rol=rol)[:5]
        context['total_usuarios'] = Usuarios.objects.filter(id_rol=rol).count()
        return context


# =============================================================================
# === VISTAS DE USUARIOS ===
# =============================================================================

@method_decorator(never_cache, name='dispatch')
class UsuarioListView(ListView):
    model = Usuarios
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        rol = self.request.GET.get('rol')
        estado = self.request.GET.get('estado')
        busqueda = self.request.GET.get('busqueda')

        if rol:
            queryset = queryset.filter(id_rol_id=rol)
        if estado:
            queryset = queryset.filter(estado=estado)
        if busqueda:
            queryset = queryset.filter(
                Q(nombres__icontains=busqueda) |
                Q(apellidos__icontains=busqueda) |
                Q(correo_usuario__icontains=busqueda) |
                Q(documento__icontains=busqueda)
            )
        return queryset.order_by('-fecha_registro')

    # Agregar datos adicionales al contexto para filtros y títulos
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Lista de Usuarios'
        context['roles'] = RolesOld.objects.all()
        context['estados'] = ['ACTIVO', 'INACTIVO', 'SUSPENDIDO']
        return context


@method_decorator(never_cache, name='dispatch')
class UsuarioCreateView(CreateView):
    model = Usuarios
    template_name = 'usuarios/usuario_form.html'
    form_class = UsuarioForm
    success_url = reverse_lazy('usuarios:usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Usuario'
        context['roles'] = RolesOld.objects.filter(deleted_at__isnull=True)
        return context

    def form_valid(self, form):
        try:
            usuario = form.save(commit=False)
            usuario.fecha_registro = timezone.now()
            usuario.save()
            
            messages.success(
                self.request, 
                f'Usuario "{usuario.get_full_name()}" creado exitosamente'
            )
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al crear: {str(e)}')
            return self.form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class UsuarioUpdateView(UpdateView):
    model = Usuarios
    template_name = 'usuarios/usuario_form.html'
    form_class = UsuarioUpdateForm
    success_url = reverse_lazy('usuarios:usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Usuario'
        context['roles'] = RolesOld.objects.filter(deleted_at__isnull=True)
        return context

    def form_valid(self, form):
        try:
            usuario = form.save(commit=False)
            usuario.updated_at = timezone.now()
            usuario.save()
            
            messages.success(
                self.request, 
                f'Usuario "{usuario.get_full_name()}" actualizado correctamente'
            )
            return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'Error al actualizar: {str(e)}')
            return self.form_invalid(form)

# Agregar vista para cambio de contraseña
class UsuarioChangePasswordView(View):
    """Vista para que el usuario cambie su propia contraseña"""
    
    def post(self, request, pk):
        try:
            usuario = get_object_or_404(Usuarios, pk=pk, deleted_at__isnull=True)
            
            old_password = request.POST.get('old_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not usuario.check_password(old_password):
                messages.error(request, "La contraseña actual es incorrecta")
                return redirect('usuarios:usuario_detail', pk=pk)
            
            if new_password != confirm_password:
                messages.error(request, "Las nuevas contraseñas no coinciden")
                return redirect('usuarios:usuario_detail', pk=pk)
            
            usuario.cambiar_contrasena(old_password, new_password)
            messages.success(request, "✓ Contraseña cambiada exitosamente")
            return redirect('usuarios:usuario_detail', pk=pk)
            
        except ValidationError as e:
            messages.error(request, f"⚠️ {str(e)}")
            return redirect('usuarios:usuario_detail', pk=pk)
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('usuarios:usuario_detail', pk=pk)
        

@method_decorator(never_cache, name='dispatch')
class UsuarioDeleteView(DeleteView):
    model = Usuarios
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuarios:usuario_list')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Usuario eliminado exitosamente')
        return response


@method_decorator(never_cache, name='dispatch')
class UsuarioDetailView(DetailView):
    model = Usuarios
    template_name = 'usuarios/usuario_detail.html'
    context_object_name = 'usuario'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['titulo'] = f'Detalle: {usuario.nombres} {usuario.apellidos}'
        context['rol_nombre'] = usuario.id_rol.nombre_rol if usuario.id_rol else "Sin rol"
        return context