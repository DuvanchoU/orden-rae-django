from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Usuarios, RolesOld
from django.contrib import messages
from django.utils import timezone


# ROLES
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
    fields = ['nombre_rol', 'descripcion']
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nuevo Rol'
        return context


class RolUpdateView(UpdateView):
    model = RolesOld
    template_name = 'usuarios/rol_form.html'
    fields = ['nombre_rol', 'descripcion']
    success_url = reverse_lazy('usuarios:rol_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Rol'
        return context


class RolDeleteView(DeleteView):
    model = RolesOld
    template_name = 'usuarios/rol_confirm_delete.html'
    success_url = reverse_lazy('usuarios:rol_list')


# USUARIOS
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
    fields = ['nombres', 'apellidos', 'documento', 'correo_usuario', 'contrasena_usuario',
              'genero', 'telefono', 'estado', 'id_rol']
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
    fields = ['nombres', 'apellidos', 'documento', 'correo_usuario',
              'genero', 'telefono', 'estado', 'id_rol']
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