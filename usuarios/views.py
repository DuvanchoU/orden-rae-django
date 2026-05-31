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
    return redirect('/login/')

# Agregar vista para logout que limpie toda la sesión y redirija al login con un mensaje de éxito indicando que se ha cerrado 
# sesión correctamente, y prevenir caché en esta vista para garantizar que no se almacene información sensible en el 
# navegador después de cerrar sesión.
@never_cache  # Previene caché en logout
def logout_view(request):
    """
    Cierra la sesión del usuario y limpia todo.
    """
    # Limpiar TODA la sesión
    request.session.flush()
    return redirect('/login/?logged_out=1')

# =============================================================================
# === VISTAS DE ROLES ===
# =============================================================================

# Agregar vista para listar roles, con paginación, búsqueda y ordenamiento, y mostrar un mensaje de éxito al eliminar un rol.
@method_decorator(never_cache, name='dispatch')
class RolListView(ListView):
    model = RolesOld
    template_name = 'usuarios/rol_list.html'
    context_object_name = 'roles'
    paginate_by = 10

    # Permitir filtrar por búsqueda general en la lista de roles utilizando el parámetro GET "busqueda", aplicando el filtro 
    # de manera que se busque el término en los campos "nombre_rol" y "descripcion"
    def get_queryset(self):
        queryset = super().get_queryset()
        busqueda = self.request.GET.get('busqueda')
        if busqueda:
            queryset = queryset.filter(
                Q(nombre_rol__icontains=busqueda) |
                Q(descripcion__icontains=busqueda)
            )
        return queryset.order_by('nombre_rol')

    # En el contexto de la lista de roles, también incluir el título "Lista de Roles" para proporcionar 
    # contexto claro al usuario sobre la información que se está mostrando.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Lista de Roles'
        return context

# Agregar vista para crear un nuevo rol, con un formulario que incluya validación de datos y manejo de errores, y mostrar un mensaje de éxito al crear un nuevo rol.
@method_decorator(never_cache, name='dispatch')
class RolCreateView(CreateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    # En el formulario de creación de un nuevo rol, mostrar el título "Nuevo Rol" para proporcionar contexto 
    # claro al usuario sobre la acción que está realizando.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Rol'
        return context

    # Al crear un nuevo rol, mostrar un mensaje de éxito para informar al usuario que el rol ha sido creado correctamente.
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Rol creado exitosamente')
        return response

# Agregar vista para editar un rol existente, con un formulario que incluya validación de datos y manejo de errores, y mostrar un mensaje de éxito al actualizar un rol.
@method_decorator(never_cache, name='dispatch')
class RolUpdateView(UpdateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    # En el formulario de edición de un rol, mostrar el nombre del rol como título para proporcionar contexto claro al usuario sobre qué rol se está editando.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Rol'
        return context

    # Al actualizar un rol, mostrar un mensaje de éxito para informar al usuario que el rol ha sido actualizado correctamente.
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Rol actualizado exitosamente')
        return response


@method_decorator(never_cache, name='dispatch')
class RolDeleteView(DeleteView):
    model = RolesOld
    template_name = 'usuarios/rol_confirm_delete.html'
    success_url = reverse_lazy('usuarios:rol_list')

    # Al eliminar un rol, mostrar un mensaje de éxito
    def form_valid(self, form):
        messages.success(self.request, 'Rol eliminado exitosamente')
        return super().form_valid(form)


@method_decorator(never_cache, name='dispatch')
class RolDetailView(DetailView):
    model = RolesOld
    template_name = 'usuarios/rol_detail.html'
    context_object_name = 'rol'
    
    # En el detalle de un rol, también mostrar una lista de los usuarios que tienen asignado ese rol, limitando a los 5 más recientes 
    # y mostrando el total de usuarios con ese rol
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

    # Permitir filtrar por rol, estado y búsqueda general en la lista de usuarios utilizando los parámetros GET "rol", "estado" y "busqueda" 
    # respectivamente, aplicando los filtros de manera combinada si se proporcionan varios parámetros y ordenando los resultados por fecha 
    # de registro de manera descendente para mostrar primero los usuarios más recientes en la parte superior de la lista.
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

    # En el contexto de la lista de usuarios, también incluir una lista de todos los roles disponibles para permitir el filtrado por rol en la interfaz, 
    # así como una lista de los posibles estados de usuario (por ejemplo, "ACTIVO", "INACTIVO", "SUSPENDIDO") para permitir el filtrado por estado en la interfaz.
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

    # En el formulario de creación de un nuevo usuario, mostrar el título "Nuevo Usuario" y una 
    # lista desplegable de roles disponibles para asignar al usuario, filtrando solo los roles que no han sido eliminados 
    # (deleted_at es null) para garantizar que solo se puedan asignar roles activos a los usuarios.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Usuario'
        context['roles'] = RolesOld.objects.filter(deleted_at__isnull=True)
        return context

    # Al crear un nuevo usuario, mostrar un mensaje de éxito con el nombre completo del usuario creado, y manejar 
    # errores en caso de que ocurra algún problema durante la creación.
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

# Agregar vista para editar un usuario existente, con un formulario que incluya validación de datos y manejo de errores, 
# y mostrar un mensaje de éxito al actualizar un usuario.
@method_decorator(never_cache, name='dispatch')
class UsuarioUpdateView(UpdateView):
    model = Usuarios
    template_name = 'usuarios/usuario_form.html'
    form_class = UsuarioUpdateForm
    success_url = reverse_lazy('usuarios:usuario_list')

    # En el formulario de edición de un usuario, mostrar el nombre completo del usuario como título, así como una 
    # lista desplegable de roles disponibles para asignar al usuario, filtrando solo los roles que no han sido eliminados 
    # (deleted_at es null) para garantizar que solo se puedan asignar roles activos a los usuarios.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Usuario'
        context['roles'] = RolesOld.objects.filter(deleted_at__isnull=True)
        return context

    # Al actualizar un usuario, mostrar un mensaje de éxito con el nombre completo del usuario actualizado, y manejar 
    # errores en caso de que ocurra algún problema durante la actualización.
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

    # En esta vista se implementa la lógica para que un usuario pueda cambiar su propia contraseña,
    # verificando que la contraseña actual sea correcta, que las nuevas contraseñas coincidan y cumplan con los requisitos 
    # de fortaleza, y mostrando mensajes de éxito o error según corresponda.  
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
        
# Agregar vista para eliminar usuario con confirmación y mensaje de éxito al eliminar un usuario, y manejo de errores en 
# caso de que ocurra algún problema durante la eliminación.
@method_decorator(never_cache, name='dispatch')
class UsuarioDeleteView(DeleteView):
    model = Usuarios
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuarios:usuario_list')

    # Al eliminar un usuario, mostrar un mensaje de éxito y manejar errores en caso de que ocurra algún problema durante la eliminación.
    def form_valid(self, form):
        messages.success(self.request, 'Usuario eliminado exitosamente')
        return super().form_valid(form)

# Agregar vista para mostrar el detalle de un usuario, incluyendo su información personal y el rol asignado, y mostrar 
# un mensaje de éxito al cargar el detalle del usuario.
@method_decorator(never_cache, name='dispatch')
class UsuarioDetailView(DetailView):
    model = Usuarios
    template_name = 'usuarios/usuario_detail.html'
    context_object_name = 'usuario'
    
    # En el detalle de un usuario, mostrar el nombre completo del usuario como título, así como el nombre del rol asignado al usuario 
    # (o "Sin rol" si no tiene un rol asignado) para proporcionar información clara sobre el usuario que se está visualizando.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['titulo'] = f'Detalle: {usuario.nombres} {usuario.apellidos}'
        context['rol_nombre'] = usuario.id_rol.nombre_rol if usuario.id_rol else "Sin rol"
        return context