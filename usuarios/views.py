from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Usuarios, RolesOld
from .forms import UsuarioForm, UsuarioUpdateForm, RolForm
from django.contrib import messages
from django.utils import timezone
import hashlib
from django.contrib.auth import login as auth_login  


# =============================================================================
# === VISTAS DE LOGIN Y LOGOUT ===
# =============================================================================

def login_view(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')      # ← Debe coincidir con name="correo"
        contrasena = request.POST.get('contrasena')  # ← Debe coincidir con name="contrasena"
        
        try:
            usuario = Usuarios.objects.get(correo_usuario=correo)
            
            # Encriptar contraseña con SHA256 (igual que cuando creaste los usuarios)
            contrasena_hash = hashlib.sha256(contrasena.encode()).hexdigest()
            
            if usuario.contrasena_usuario == contrasena_hash:
                
                if usuario.estado != 'ACTIVO':
                    messages.error(request, 'Usuario inactivo.')
                    return render(request, 'pagina/login.html')
                
                # Guardar en sesión para tu middleware
                request.session['usuario_id'] = usuario.id_usuario
                request.session['usuario_nombre'] = f"{usuario.nombres} {usuario.apellidos}"
                request.session['usuario_rol'] = usuario.id_rol.nombre_rol
                
                # Redirigir al dashboard (que manejará la redirección por rol)
                return redirect('dashboard:dashboard_home')
            else:
                messages.error(request, 'Contraseña incorrecta')
                
        except Usuarios.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
        
        return render(request, 'pagina/login.html')
    
    return render(request, 'pagina/login.html')


def logout_view(request):
    """
    Cierra la sesión del usuario y redirige al login.
    """
    from django.contrib.auth import logout as django_logout
    
    # Limpiar sesión de Django (si se usa auth_login)
    django_logout(request)
    
    # Limpiar sesión personalizada
    request.session.flush()
    
    # ✅ Redirigir al login (debe coincidir con el name en config/urls.py)
    return redirect('login')  # name='login' está en config/urls.py línea 14


# =============================================================================
# === VISTAS DE ROLES ===
# =============================================================================

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
        return context


class RolCreateView(CreateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Rol'
        return context


class RolUpdateView(UpdateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    form_class = RolForm
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Rol'
        return context


class RolDeleteView(DeleteView):
    model = RolesOld
    template_name = 'usuarios/rol_confirm_delete.html'
    success_url = reverse_lazy('usuarios:rol_list')


class RolDetailView(DetailView):
    model = RolesOld
    template_name = 'usuarios/rol_detail.html'
    context_object_name = 'rol'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rol = self.get_object()
        context['usuarios_con_rol'] = Usuarios.objects.filter(id_rol=rol)[:5]
        context['total_usuarios'] = Usuarios.objects.filter(id_rol=rol).count()
        return context


# =============================================================================
# === VISTAS DE USUARIOS ===
# =============================================================================

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = RolesOld.objects.all()
        context['estados'] = ['ACTIVO', 'INACTIVO', 'SUSPENDIDO']
        return context


class UsuarioCreateView(CreateView):
    model = Usuarios
    template_name = 'usuarios/usuario_form.html'
    form_class = UsuarioForm
    success_url = reverse_lazy('usuarios:usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Usuario'
        context['roles'] = RolesOld.objects.all()
        return context

    def form_valid(self, form):
        form.instance.fecha_registro = timezone.now()
        return super().form_valid(form)


class UsuarioUpdateView(UpdateView):
    model = Usuarios
    template_name = 'usuarios/usuario_form.html'
    form_class = UsuarioForm
    success_url = reverse_lazy('usuarios:usuario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Usuario'
        context['roles'] = RolesOld.objects.all()
        return context


class UsuarioDeleteView(DeleteView):
    model = Usuarios
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuarios:usuario_list')


class UsuarioDetailView(DetailView):
    model = Usuarios
    template_name = 'usuarios/usuario_detail.html'
    context_object_name = 'usuario'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.get_object()
        context['rol_nombre'] = usuario.id_rol.nombre_rol if usuario.id_rol else "Sin rol"
        return context