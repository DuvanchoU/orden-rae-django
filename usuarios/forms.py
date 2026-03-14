from django import forms
from .models import Usuarios, RolesOld

class UsuarioForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
            ('SUSPENDIDO', 'SUSPENDIDO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Campo de género con opciones predefinidas
    genero = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el género'),
            ('M', 'Masculino'),
            ('F', 'Femenino'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Usuarios
        fields = ['nombres', 'apellidos', 'documento', 'correo_usuario', 
                  'contrasena_usuario', 'telefono', 'genero', 'id_rol', 'estado']
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombres del usuario'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellidos del usuario'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Número de documento'
            }),
            'correo_usuario': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'correo@ejemplo.com'
            }),
            'contrasena_usuario': forms.PasswordInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Contraseña'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+57 300 123 4567'
            }),
            'id_rol': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el texto de los selects
        self.fields['id_rol'].empty_label = "Seleccione un rol"
        # No necesitamos empty_label para estado y genero porque ya los definimos en choices


# Formulario para editar (sin contraseña)
class UsuarioUpdateForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('ACTIVO', 'ACTIVO'),
            ('INACTIVO', 'INACTIVO'),
            ('SUSPENDIDO', 'SUSPENDIDO'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Campo de género con opciones predefinidas
    genero = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el género'),
            ('M', 'Masculino'),
            ('F', 'Femenino'),
            ('O', 'Otro'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    class Meta:
        model = Usuarios
        fields = ['nombres', 'apellidos', 'documento', 'correo_usuario', 
                  'telefono', 'genero', 'id_rol', 'estado']
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombres del usuario'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellidos del usuario'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Número de documento'
            }),
            'correo_usuario': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '+57 300 123 4567'
            }),
            'id_rol': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_rol'].empty_label = "Seleccione un rol"


class RolForm(forms.ModelForm):
    class Meta:
        model = RolesOld
        fields = ['nombre_rol', 'descripcion']
        widgets = {
            'nombre_rol': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Administrador'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe las funciones y permisos de este rol'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre_rol'].required = True